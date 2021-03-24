from netmiko import Netmiko
from getpass import getpass
import re
import datetime, time
from colorama import Fore


def isTimeFormat(input):
    try:
        time.strptime(input, '%H:%M:%S')
        return True
    except ValueError:
        return False

def getspantreeport(ssh):
    spanningtree = ssh.send_command("show spanning-tree detail | include from|last")
    shortest = "23:59:59"
    my_lasttime = "23:59:58"
    my_lastfrom = ""
    neighbor_ip=""
    t_shortest = datetime.datetime.strptime( shortest, '%H:%M:%S').time()
    for line in spanningtree.split("\n"):
        if "last" in line:
            lasttime = line.split()[-2:-1][0]
            if not isTimeFormat(lasttime):
                lasttime = "23:59:59"
                # print ("Not in last 24 Hours")
            # print (lasttime)
            t_lasttime = datetime.datetime.strptime( lasttime, '%H:%M:%S').time()
        if "from" in line:
            lastfrom = line.split()[-1]
            # print (lastfrom)
            if t_lasttime < t_shortest:
                t_lasttime = datetime.datetime.strptime( lasttime, '%H:%M:%S').time()
                t_shortest = datetime.datetime.strptime( lasttime, '%H:%M:%S').time()
                my_lastfrom = lastfrom
                my_lasttime = lasttime
    print ("Latest Spannigtree-Topology Change "+my_lasttime+" ago from "+my_lastfrom)
    print ("Try to find CDP-Neigbor on Interface "+my_lastfrom)
    return(my_lastfrom)

def findport_on_stack(ssh):
    try:
        print ("Switch is Stack, Try to find port on Stackmembers")
        stackmembers = ssh.send_command("show switch")
        for stackmember in stackmembers.split("\n"):
            firstword = stackmember.split()[0]
            if "Switch" in firstword:
                continue
            if "H/W" in firstword:
                continue
            if "----" in firstword:
                continue
            if "*" not in firstword:
                stacknumber = firstword[0]
                print ("changing to Stackmember "+stacknumber)
                ssh.send_command("session "+stacknumber,auto_find_prompt=False) 
                ssh.send_command("terminal length 0")  # have to reinit the terminal settings because of session command
                ssh.send_command("terminal with 512")
                port = getspantreeport(ssh)
                if  "Stack" not in port:
                    break
        return(port)
    except Exception as e:
        print (e)

#########################       
#
#      MAIN Programm
#      init variables
#
#########################

seeddevice = input("IP-Adress of Seeddevice: ")
username = input ("Username to Connect to Network-Devices: ")
password = getpass("Password for user "+username+":")

hoplist = []
hopcount = 0

device = {
    'device_type': 'cisco_ios',
    'host':seeddevice,
    'username': username,
    'password': password}

print ("Try to Connect to seeddevice :"+seeddevice+"\n")

try:
    while True:
        ssh = Netmiko(**device)
        hostname = ssh.find_prompt()[:-1]
        print (Fore.GREEN+"Connected to",hostname,Fore.RESET)
        if hostname in hoplist:
            print ("-"*30)
            print (Fore.RED,"Loop dedected : Device "+hostname+" allready parsed! ")
            print (Fore.RESET)
            quit()
        hoplist.append(hostname)
        hopcount += 1
        
        port = getspantreeport(ssh)
        
        ################################
        #    Find CDP Nei on the Port
        ################################

        try:
            neighbor_ip = ""
            if port[0:5]=="Stack":
                port = findport_on_stack(ssh)    
            cdp_nei = ssh.send_command("show cdp neighbor detail",use_textfsm=True)
            if port[0:2]=="Po":
                sh_int=ssh.send_command("show int "+port)
                for line in sh_int.split("\n"):
                    if "Members in this" in line:
                        port = line.split()[-1]
                        print ("Spanningtee Change on Portchannel! One Member is ",port) 
                        if "Hu" == port[0:2]:
                            port = port.replace("Hu","HundredGigE")
                        if "Fo" == port[0:2]:
                            port = port.replace("Fo","FortyGigabitEthernet")
                        if "TW" == port[0:2]:
                            port = port.replace("Tw","TwentyFiveGigE")
                        if "Gi" == port[0:2]:
                            port = port.replace("Gi","GigabitEthernet")
                        if "Te" == port[0:2]:
                            port = port.replace("Te","TenGigabitEthernet")
                        if "Fa" == port[0:2]:
                            port = port.replace("Fa","FastEthernet")
                        if "Eth" == port[0:3]:
                            port = port.replace("Eth","Ethernet")

            if port[0:2]=="po":
                sh_int=ssh.send_command("show int "+port)
                for line in sh_int.split("\n"):
                    if "Members in this" in line:
                        port = line.split()[-1]
                        print ("Spanningtee Change on Portchannel! One Member is ",port) 
                        if "Hu" == port[0:2]:
                            port = port.replace("Hu","HundredGigE")
                        if "Fo" == port[0:2]:
                            port = port.replace("Fo","FortyGigabitEthernet")
                        if "TW" == port[0:2]:
                            port = port.replace("Tw","TwentyFiveGigE")
                        if "Gi" == port[0:2]:
                            port = port.replace("Gi","GigabitEthernet")
                        if "Te" == port[0:2]:
                            port = port.replace("Te","TenGigabitEthernet")
                        if "Fa" == port[0:2]:
                            port = port.replace("Fa","FastEthernet")
                        if "Eth" == port[0:3]:
                            port = port.replace("Eth","Ethernet")   

            if device["device_type"] == "cisco_ios":
                # print ("IOS Device")   
                for element in cdp_nei:
                    if element["local_port"] == port:
                                neighbor_ip = element["management_ip"]
                                neighbor = element["destination_host"]
                                sw_version = element["software_version"]
                                if "(NX-OS)" in sw_version:
                                    device_type  = "cisco_nxos"
                                if "IOS" in sw_version:
                                    device_type = "cisco_ios" 
            
            if device["device_type"] == "cisco_nxos":
                # print ("NXOS DEvice")
                for element in cdp_nei:
                    if element["local_port"] == port:
                                neighbor_ip = element["mgmt_ip"]
                                neighbor = element["dest_host"]
                                sw_version = element["version"]
                                if "(NX-OS)" in sw_version:
                                    device_type  = "cisco_nxos"
                                if "IOS" in sw_version:
                                    device_type = "cisco_ios" 

            if neighbor_ip =="":
                print ("\nNo CDP Neighbor on Switch ",hostname,", Port:",port, "\n We needet ",hopcount," Hops")
                print ("-"*60)
                interface_cfg = ssh.send_command("show running-config interface "+port)
                print ("Configuration for Port "+port)
                print (interface_cfg)
                print ("-"*60)
                quit()

            New_Device = {"device_type":device_type,"host":neighbor_ip,'username': username, "password":password,  }
            device = New_Device 
        except Exception as e:
            print (Fore.RED)
            print (e)
            print (Fore.RESET)
            quit()
        ssh.cleanup()
        print ("Disconnected from Device")
        print ("Try to Connect to "+device["host"]+"\n")

except Exception as e:
    print (Fore.RED)
    print (e) 
    print (Fore.RESET)
        
