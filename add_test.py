from typing_extensions import final
from django.utils.text import slugify

from dcim.choices import *
from dcim.models import Cable, Device, DeviceRole, DeviceType, Platform, Rack, RackRole, Site, Manufacturer
from dcim.models.device_components import FrontPort, Interface, RearPort
from tenancy.models import TenantGroup, Tenant
from ipam.choices import *
from ipam.models import IPAddress, Prefix, Role, VLAN, VLANGroup

from extras.scripts import *
##TESTE##

class ProvisionMDevices (Script):
	class Meta:
		name = "Provision Devices"
		description = "Provision multiples Devices to a Site"
		field_order = ['site']
		#commit_default = False

	# Drop down for sites
	site = ObjectVar (
		description = "Site to be deployed",
		queryset = Site.objects.all ()
	)
	
	tenant_group = ObjectVar(
		model=TenantGroup,
		default='25'	#change to production id
	)
	site_tenant = ObjectVar(
		label='Tenant',
		model=Tenant,
		display_field='model',
		query_params={
			'group_id': '$tenant_group'
		}
	)
	devices_name = StringVar( 
		description="Devices name prefix whitout numbers, ej UYSCMV"
	)
	firewall_manufacturer = ObjectVar(
		model=Manufacturer,
		default='22',	#change to production id
		required=False 
	)

	firewall_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$firewall_manufacturer'} 
	)
	core_manufacturer = ObjectVar(
		model=Manufacturer,
		default='2',	#change to production id
		required=False 
	)

	core_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$core_manufacturer'} 
	)
	cam_manufacturer = ObjectVar(
		model=Manufacturer,
		default='23',	#change to production id
		required=False 
	)

	cam_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$cam_manufacturer'} 
	)
	iap_manufacturer = ObjectVar(
		model=Manufacturer,
		default='10',	#change to production id
		required=False 
	)

	iap_model = ObjectVar(
		model=DeviceType, 
		display_field='model', 
		query_params={'manufacturer_id': '$iap_manufacturer'} 
	)
	device_status = ChoiceVar (
		DeviceStatusChoices, 
		default=DeviceStatusChoices.STATUS_PLANNED, 
		label='Device Status'
	)
	'''devices_role = ObjectVar(		model=DeviceRole,		required=False 	) '''   #FAZER FIXO !!!!!!


################################################################################             
#                  Methods                                                    #
################################################################################
	def create_rack (self, site):
		rname = '{} - CPD'.format(site)
		try:
			rack = Rack.objects.get (name = rname)
			self.log_info ("Rack %s already present, carrying on." % rack)
			return rack
		except Rack.DoesNotExist:
			pass

		rack = Rack (
			role = RackRole.objects.get (name = 'CPD'),
			width = RackWidthChoices.WIDTH_19IN,
			u_height = 42,
			status = RackStatusChoices.STATUS_PLANNED,
			name = rname,
			site = site
		)

		rack.save ()
		self.log_success ("Created rack {}".format (rack))
		return rack

	def setup_device(self, site, rack, sitetenant, devicesname, devicemodel, devicestatus, manufacturer, primary):
			if primary == 1:
				box = '1'
			else:
				box = '2'
			if manufacturer.name != 'Aruba':
				pfx = Prefix.objects.get(site = site, vlan__vid=100) 
				vlanid = 'vlan100'
				if manufacturer.name == 'Fortinet':
					vlanid = 'dmz'
					device_ip = pfx.prefix[10]
					device_name = devicesname + 'FWP001-' + box
					role = DeviceRole.objects.get (name = 'Firewall')
					if primary == 1:
						rack_u = rack.u_height - 10
				elif manufacturer.name == 'Cisco':
					device_ip = pfx.prefix[2]
					device_name = devicesname + 'CRP001-' + box
					role = DeviceRole.objects.get (name = 'Core Switch')
					if primary == 1:
						rack_u = rack.u_height - 12
					else:
						rack_u = rack.u_height - 14
				elif manufacturer.name == 'Ruckus':
					device_ip = pfx.prefix[5]
					device_name = devicesname + 'CCAM001-' + box
					role = DeviceRole.objects.get (name = 'Core Cameras')
					rack_u = rack.u_height - 16
			elif manufacturer.name == 'Aruba': 
				pfx = Prefix.objects.get(site = site, vlan__vid=20) 
				vlanid = 'vlan20'
				device_ip = pfx.prefix[2]
				device_name = devicesname + 'CTP001'
				role = DeviceRole.objects.get (name = 'Controller')

			try: 
				device = Device.objects.get (name = device_name)
				self.log_info ("Device %s already present, carryng on." % device_name)

				return device
			except Device.DoesNotExist:
				pass
			
			device = Device(
				site = site,
				tenant = sitetenant,
				name = device_name,
				device_type = devicemodel,
				status = devicestatus,
				device_role = role,
				rack = rack,
				face = DeviceFaceChoices.FACE_FRONT
				
			)
			device.save()
			self.log_success('Created device %s' % device)
			try:
				device.position = rack_u
				device.save()
			except:
				pass
			#set up mgmt IP
			if primary == 1:
				device_iface = Interface.objects.get (device = device, name = vlanid)
				try:
					device_iface = IPAddress.objects.get (address = device_ip)
					self.log_info("Ip %s already present, carryng on" % device_ip)

				except IPAddress.DoesNotExist:
					device_mgmt_ip = IPAddress (address = device_ip)
					device_mgmt_ip.save ()
				finally:
					if device_mgmt_ip.assigned_object is None: 
						device_mgmt_ip.assigned_object = device_iface
						device_mgmt_ip.save ()
						device.primary_ip4 = device_mgmt_ip
						device.save()
						self.log_success ("Configured %s on interface %s of %s" % (device_mgmt_ip, device_iface, device))
					else:
						self.log_info ("Ip %s is already in use for another interface" % (device_mgmt_ip))

			return device

	def setup_cable(self, fw_1, fw_2,firewallmodel,sw_1,sw_2, coremanufacturer, coremodel,cam_1,ap_c):
		sw24p = list(DeviceType.objects.filter(model__icontains='24p').values_list('model', flat='true')) #get all 24p switches
		sw48p = list(DeviceType.objects.filter(model__icontains='48p').values_list('model', flat='true')) #get all 24p switches
		def device_cable(device1, device2, if1, if2, color, type, label):
			try:
				cable = Cable (
					termination_a = Interface.objects.get (device = device1, name = if1),
					termination_b = Interface.objects.get (device = device2, name = if2),
					type = type,
					color = color,
					label = label,
					status = CableStatusChoices.STATUS_PLANNED
				)
				cable.save ()
				self.log_success ("added cable between %s interface %s and %s interface %s" % (device1,if1, device2,if2))
			except:
				self.log_info ("cable between %s interface %s and %s interface %s already exists, or interfaces doesn't exists, carryng on" % (device1,if1, device2,if2))
				pass
		def setup_stack(device1, device2, if1, if2, color, type, label):
			try:
				cable = Cable (
					termination_a = RearPort.objects.get (device = device1, name = if1),
					termination_b = RearPort.objects.get (device = device2, name = if2),
					type = type,
					color = color,
					label = label,
					status = CableStatusChoices.STATUS_PLANNED
				)
				cable.save ()
				self.log_success ("added cable between %s interface %s and %s interface %s" % (device1,if1, device2,if2))
			except:
				self.log_info ("cable between %s interface %s and %s interface %s already exists, or interfaces doesn't exists, carryng on" % (device1,if1, device2,if2))
				pass
		
		if str(firewallmodel) == 'Fortigate-60F':
			device_cable(fw_1,fw_2,'porta','porta','607d8b','cat6','HA') 			#firewall HA1
			device_cable(fw_1,fw_2,'portb','portb','607d8b','cat6','HA') 			#firewall HA2
		else:	
			device_cable(fw_1,fw_2,'port6','port6','607d8b','cat6','HA') 			#firewall HA1
			device_cable(fw_1,fw_2,'port7','port7','607d8b','cat6','HA') 			#firewall HA2
		
		if str(coremodel) in list(sw24p):
			device_cable(fw_1,sw_1,'dmz','G1/0/23','3f51b5','cat6','HA') 			#dmz_fw1 to core_1
			device_cable(fw_2,sw_2,'dmz','G1/0/23','3f51b5','cat6','HA')			#dmz_fw2 to core_2
		elif str(coremodel) in list(sw48p):
			device_cable(fw_1,sw_1,'dmz','G1/0/47','3f51b5','cat6','HA') 			#dmz_fw1 to core_1
			device_cable(fw_2,sw_2,'dmz','G1/0/47','3f51b5','cat6','HA')			#dmz_fw2 to core_2
		
		device_cable(fw_1,sw_1,'port1','G1/0/1','00bcd4','cat6','PO1')			#PO_fw1
		device_cable(fw_1,sw_2,'port2','G1/0/1','00bcd4','cat6','PO1')			#PO_fw1
		device_cable(fw_2,sw_1,'port1','G1/0/2','00bcd4','cat6','PO2')			#PO_fw2
		device_cable(fw_2,sw_2,'port2','G1/0/2','00bcd4','cat6','PO2')			#PO_fw2
		device_cable(sw_1,ap_c,'G1/0/3','G1/0/1','3f51b5','cat6','controller')	#aruba controller
		if str(coremanufacturer) == 'Cisco':
			if str(coremodel) == 'Catalyst 1000-24P':
				device_cable(sw_1,sw_2,'G1/0/26','G1/0/26','ff9800','Singlemode Fiber','fiber - stack')	#Cores Stack
				device_cable(sw_1,sw_2,'G1/0/27','G1/0/27','ff9800','Singlemode Fiber','fiber - stack')	#Cores Stack
			else:
				setup_stack(sw_1,sw_2,'Stack01','Stack02','111111','Direct Attach Copper (Active)','stack wise')	#Cores Stack
				setup_stack(sw_1,sw_2,'Stack02','Stack01','111111','Direct Attach Copper (Active)','stack wise')	#Cores Stack

		
	def run (self, data, commit):
		site = data['site']
		sitetenant = data['site_tenant']
		devicesname = data['devices_name']
		firewallmodel = data['firewall_model']
		firewallmanufacturer = data['firewall_manufacturer']
		coremanufacturer = data['core_manufacturer']
		cammanufacturer = data['cam_manufacturer']
		iapmanufacturer = data['iap_manufacturer']
		coremodel = data['core_model']
		cammodel = data['cam_model']
		iapmodel = data['iap_model']
		devicestatus = data['device_status']

		rack = self.create_rack(site)
		fw = self.setup_device( site, rack, sitetenant, devicesname, firewallmodel, devicestatus, firewallmanufacturer, 1)
		fw2 = self.setup_device( site, rack, sitetenant, devicesname, firewallmodel, devicestatus, firewallmanufacturer, 2)
		sw = self.setup_device( site, rack, sitetenant, devicesname, coremodel, devicestatus, coremanufacturer, 1)
		sw2 = self.setup_device( site, rack, sitetenant, devicesname, coremodel, devicestatus, coremanufacturer, 2)
		cam = self.setup_device( site, rack, sitetenant, devicesname, cammodel, devicestatus, cammanufacturer, 1)
		iap = self.setup_device( site, rack, sitetenant, devicesname, iapmodel, devicestatus, iapmanufacturer, 1)
		self.setup_cable(fw, fw2, firewallmodel,sw,sw2,coremodel, coremanufacturer, cam,iap)




# criar devices OK 
# 		criar devices secundarios ok
#			cabear devices (falta ruckus e cisco stack 9200 e 1000)
#				criar chassis

# inserir ip nos devices OK

# criar rack ok
#	inserir devices no rack ok

# 
# 
#

# Gerar output para criar arquivos????
# SCRIPT PARA WAN?????
#SCRIPT PARA POR EM ACTIVE!!
