from math import floor

def validaOct(num):
	'''
	altera octeto para o octeto de rede /22
	'''
	b = int(num)/4
	numf = 4 * floor(b)
	return numf

def validaIp(addr, ipaddr):
	'''
	valida se ip esta dentro da faixa 0 a 255
	'''
	addr = int(addr)
	if addr > 255:
		print('invalid ip address {}'.format(ipaddr))
		quit()
	else:
		return addr

desc = ['VLAN_MGMT','VLAN_IS','VLAN_CLOCK','VLAN_WIFI','VLAN_PRINTERS','VLAN_HANDHELD','VLAN_OPERATOR','VLAN_CAMERAS','VLAN_CORP']

def childprefix (a, b):
	gen_ips['subrede'].append(a)
	gen_ips['desc'].append(b)
	if '/' in a:
		ips = a.split('/')
		ip = ips[0]
		mask = ips[1]
		if '.' in ip:
			ipr = ip.split('.')

		if mask == '22':
			oct1 = int(ipr[0])
			oct1 = validaIp(oct1, a)
			oct2 = int(ipr[1])
			oct2 = validaIp(oct2, a)
			oct3 = int(ipr[2])
			oct3 = validaOct(oct3)
			oct3 = validaIp(oct3, a)
			ch3 = [oct3,oct3,oct3,oct3,oct3,oct3,oct3+1,oct3+2,oct3+2]
			ch4 = [0,16,24,32,64,128,0,0,128]
			nmask = [28,28,28,27,26,25,24,25,25]
			count_m = len(nmask)
			for x in range(0, count_m):
				printIps(nmask[x], oct1, oct2, ch3[x], ch4[x], desc[x])

		else:
			print ('mascara ainda nao programada ' + a)

def printIps(nmask, oct1, oct2, oct3, oct4, desc):
	#print ('{}.{}.{}.{}/{} - {}'.format(oct1,oct2,oct3,oct4,nmask,desc))
	gen_ips['subrede'].append('{}.{}.{}.{}/{}'.format(oct1,oct2,oct3,oct4,nmask))
	gen_ips['desc'].append(desc)

gen_ips = {'subrede': [],'desc': []}

#a = input("Enter ip address: ") #for manual testing
#b = input("Enter desc: ") #for manual testing
#childprefix(a,b)
#print(gen_ips['subrede'][0], gen_ips['desc'][0])
#print(gen_ips['subrede'][2], gen_ips['desc'][1])
#  X.Y.Z.0   / 28   -   mgmt 	#  X.Y.Z.16  / 28   -   is			#  X.Y.Z.24  / 28   -   REP 
#  X.Y.Z.32  / 27   -   Aruba 	#  X.Y.Z.64  / 26   -   Printers 	#  X.Y.Z.128 / 25   -   HH
#  X.Y.Z+1.0 / 24   -   OP 		#  X.Y.Z+2.0 /	25   -   Cam  		#  X.Y.Z+2.128 / 25   -   corp
