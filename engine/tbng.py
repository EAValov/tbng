#!/usr/bin/env python3
#


# import modules used here -- sys is a very standard one
import sys,argparse,logging,os,json,subprocess
from libraries import utility
from libraries.plugin_loader import run_plugin

__version_info__ = ('0', '9', '0')
__version__ = '.'.join(__version_info__)

#Getting path for config usage

current_dir = os.path.dirname(os.path.abspath(__file__))
configuration = None
config_path = current_dir+"/../config/tbng.json"
runtime= {}
runtime_path = current_dir+"/../config/runtime.json"


torrc="/etc/tor/torrc"
config_prefix='#TBNG_Autogenerated_-_do_not_edit_'

# Gather our code in a main() function
def main(args, loglevel):
  global configuration
  global runtime
  logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

  with open(config_path) as data_file:    
    configuration = json.load(data_file)
  logging.debug("Configuration loaded from file {0}".format(config_path))

    
  if os.path.isfile(runtime_path):
    with open(runtime_path) as data_file:    
      runtime = json.load(data_file)
    logging.debug("Runtime data loaded from file {0}".format(runtime_path))
  else:
    ### default runtime is here
    runtime['mode']="direct"
    runtime['tor_bridges']={}
    runtime['tor_bridges']['mode']="none"
    runtime['tor_bridges']['bridges']=[]
    runtime['tor_excluded_countries']=[]
    logging.debug("Runtime not found, creating default")
    update_runtime()
   
  logging.debug("Configuration dump: {0}".format(configuration))
  logging.debug("Runtime dump: {0}".format(runtime))
  # Actual code starts here
  logging.debug("We are running in {0}".format(current_dir))
  logging.debug("Your Command: {0}".format(args.command))
  logging.debug("Options are: {0}".format(args.options))
  
  choices = {   #do not use ()
   'chkconfig': [chkconfig, "Check configuration"],
   'masquerade': [masquerade, "Enables masquerading on all WAN interfaces"],
   'clean_firewall': [clean_fw, "Cleans firewall settings"],
   'mode': [mode, "Sets operation mode - can be direct,tor,privoxy or restore to restore from saved runtime"],
   'reboot': [reboot, "Reboots system"],
   'shutdown': [shutdown,"Shutdowns system"],
   'halt': [halt, "Halts system"],
   'tor_restart': [tor_restart, "Restarts TOR service"],
   'tor_stop': [tor_stop,"Stops TOR service"],
   'i2p_restart': [i2p_restart, "(Re)starts i2p service"],
   'i2p_stop': [i2p_stop, "Stops i2p service"],
   'get_default_interface': [get_default_interface, "Prints default interface or raises an exception in case iface not in wan list"],
   'set_default_interface': [set_default_interface, "Sets default interface, raises exception if interface not in wan list."],
   'probe_obfs': [probe_obfs, "Returns available obfsproxy options"],
   'tor_bridge': [tor_bridge, "Configures tor bridge - json string with settings must be passed"],
   'tor_reset': [tor_reset, "Resets tor configuration to default by removing bridges and excluded countries setting"],
   'tor_exclude_exit': [tor_exclude_exit, "Exclude TOR exit nodes by country - parameter is json array of countries"],
   'get_cpu_temp': [get_cpu_temp, "Prints CPU temperature (plugin must be configured"],
   'macspoof_wan': [macspoof_wan, "Spoofs MAC address of WAN interface (plugin must be configured)"],
   'patch_nmcli': [patch_nmcli, "Set sticky bit and readonly to nmcli binary for easy patching after system update" ],
   'help': [help, "Prints list of available commands"],
   'version': [version, "Show version info"],
   'unknown': [unknown, "This is a stub for unknown options"]
  }
  
  if args.command == 'help':
    for key, value in choices.items():
      if key != 'unknown':
        print("{0} - {1}".format(key,value[1]))
  else:
    runfunc = choices[args.command][0] if choices.get(args.command) else unknown
    runfunc(args.options)  
  
#options checker

def check_options(options,num):
  if num!=len(options):
    raise Exception("Illegal number of options, required number is {0}".format(num))  

#function implementation goes here
def unknown(options):
 raise Exception("Unknown options passed")

def chkconfig(options):
  check_options(options,0)
  ##getting interface list
  iface_list = os.listdir("/sys/class/net")
  logging.debug("Interface list: {0}".format(iface_list))
  ##checking WAN interfaces
  wireless=0
  wired=0

  if ('wan_interface' not in configuration.keys()) or (not configuration['wan_interface']):
   raise Exception("No WAN interfaces configured")
     
  for interface in configuration['wan_interface']:
    if interface['name'] not in iface_list:
      raise Exception("WAN interface {0} is not defined or does not exist in /sys/class/net".format(interface['name']))
    else: 
      if is_wireless(configuration['wan_interface'],interface['name']):
        wireless +=1
      else:
        wired +=1

  if ( wireless > 1 ):
    raise Exception("Only one WAN wireless interface is allowed")

  #checking LAN Interfaces
  if ('lan_interface' not in configuration.keys()) or (not configuration['lan_interface']):
   raise Exception("No LAN interface configured")

  for interface in configuration['lan_interface']:
    if interface['name'] not in iface_list:
      raise Exception("LAN interface {0} is not defined or does not exist in /sys/class/net".format(interface['name']))
  
  #Checking interface conflicts
  lans=[]
  for interface in configuration['lan_interface']:
    lans.append(interface['name'])
  wans=[]
  for interface in configuration['wan_interface']:
    wans.append(interface['name'])

  if len(set(lans).intersection(wans)) > 0:
   raise Exception("Conflicting interfaces in LAN and WAN are detected: {0}".format(set(lans).intersection(wans)))
 

  logging.info("Check config called")

def masquerade(options):
  check_options(options,0)
  # template
  Script=""
  # Making list of wan interfaces

  for interface in configuration['wan_interface']:
    Script = Script + "iptables --table nat --append POSTROUTING --out-interface {0} -j MASQUERADE\n".format(interface['name']) 
  
  for interface in configuration['lan_interface']:
    Script = Script + "iptables --append FORWARD --in-interface {0} -j ACCEPT\n".format(interface['name']) 

  Script = Script + "iptables -A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT\n" 
  Script = Script + "sysctl -w net.ipv4.ip_forward=1\n"

  logging.debug(utility.run_multi_shell_command(Script).decode("utf-8"))
  logging.info("Masquerading called")

def clean_fw(options):
  check_options(options,0)
  logging.debug(utility.run_multi_shell_command("""iptables -F
  iptables -X
  iptables -t nat -F
  iptables -t nat -X
  iptables -t mangle -F
  iptables -t mangle -X
  iptables -t raw -F
  iptables -t raw -X
  iptables -P INPUT ACCEPT
  iptables -P FORWARD ACCEPT
  iptables -P OUTPUT ACCEPT""").decode("utf-8"))
  logging.info("Clean firewall called")

def mode(options):
  check_options(options,1)
  
  if options[0] not in  ['direct','tor','privoxy','restore']:
    raise Exception("Illegal mode")
  
  if options[0] == 'restore':     
    options[0] = runtime['mode']
  commandMode=""
  for interface in configuration['lan_interface']:
    if options[0] == 'privoxy':
      commandMode  += "iptables -t nat -A PREROUTING -i {0} -p tcp --dport 80 -j REDIRECT --to-port 8118\n".format(interface['name'])
    commandMode += "iptables -t nat -A PREROUTING -i {0} -p udp --dport 53 -j REDIRECT --to-ports 9053\n".format(interface['name'])  
    commandMode += "iptables -t nat -A PREROUTING -i {0} -p tcp --syn -j REDIRECT --to-ports 9040\n".format(interface['name'])


  clean_fw([])

  allowed_ports_tcp=[22,3000]
  allowed_ports_udp=[]
  if ('allowed_ports_tcp' in configuration.keys()):
    #Ports 22 and 3000 are allowed by default
    allowed_ports_tcp = list(set([22,3000]+configuration['allowed_ports_tcp']))

  if ('allowed_ports_udp' in configuration.keys()):
    allowed_ports_udp = list(set([]+configuration['allowed_ports_udp']))
  
  commandAllow="sysctl -w net.ipv4.ip_forward=1\n" #must run always
  for interface in configuration['lan_interface']:
    for port in allowed_ports_tcp:
      commandAllow = commandAllow + "iptables -t nat -A PREROUTING -i {0} -p tcp --dport {1} -j REDIRECT --to-port {1}\n".format(interface['name'],port)  
    for port in allowed_ports_udp:
      commandAllow = commandAllow + "iptables -t nat -A PREROUTING -i {0} -p udp --dport {1} -j REDIRECT --to-port {1}\n".format(interface['name'],port)
  logging.debug("Allowed LAN service ports: \n{0}\n".format(commandAllow))   
  logging.debug(utility.run_multi_shell_command(commandAllow).decode("utf-8"))

  if options[0] in ['tor','privoxy']:
    logging.debug("Running command: \n{0}\n".format(commandMode))
    logging.debug(utility.run_multi_shell_command(commandMode).decode("utf-8"))
  else:
    masquerade([])

  #Locking firewall if needed
  commandLock = "iptables  -A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT\n"
  allowed_ports_wan_tcp=[]
  if ('allowed_ports_wan_tcp' in configuration.keys()):
    allowed_ports_wan_tcp = list(set([]+configuration['allowed_ports_wan_tcp']))

  allowed_ports_wan_udp=[]
  if ('allowed_ports_wan_udp' in configuration.keys()):
    allowed_ports_wan_udp = list(set([]+configuration['allowed_ports_wan_udp']))

  #Allowing Wan ports if any
  for interface in configuration['wan_interface']:
    for port in allowed_ports_wan_tcp:
      commandLock = commandLock + "iptables -A INPUT -i {0} -p tcp --dport {1} -j ACCEPT\n".format(interface['name'],port)
    for port in allowed_ports_wan_udp:
      commandLock = commandLock + "iptables -A INPUT -i {0} -p udp --dport {1} -j ACCEPT\n".format(interface['name'],port)
 
  for interface in configuration['wan_interface']:
   commandLock = commandLock + "iptables -A INPUT -i {0} -j DROP\n".format(interface['name'])
  
  if configuration['lock_firewall']:
    logging.debug("Locking WAN with exceptions:\n{0}\n".format(commandLock))
    logging.debug(utility.run_multi_shell_command(commandLock).decode("utf-8"))
  
  runtime['mode']=options[0]
  update_runtime()

  #calling tor_bridges

  tor_bridge([json.dumps(runtime['tor_bridges'])])
  tor_exclude_exit([json.dumps(runtime['tor_excluded_countries'])])

  logging.info("Mode setting called - mode {0} selected".format(options[0]))  

def reboot(options):
  check_options(options,0)
  logging.info("Reboot called")
  logging.debug(utility.run_shell_command("reboot").decode("utf-8"))
  
def shutdown(options):
  check_options(options,0)
  logging.info("Shutdown called")
  logging.debug(utility.run_shell_command("shutdown -h now").decode("utf-8"))

def halt(options):
  check_options(options,0)
  logging.info("Halt called")
  logging.debug(utility.run_shell_command("shutdown -H now").decode("utf-8"))

def tor_restart(options):
  check_options(options,0)
  logging.debug(utility.run_shell_command("systemctl restart tor").decode("utf-8"))
  logging.info("TOR Restart called")

def tor_stop(options):
  check_options(options,0)
  mode(["direct"])
  logging.debug(utility.run_shell_command("systemctl stop tor").decode("utf-8"))
  logging.info("TOR Stop called")

def i2p_restart(options):
  check_options(options,0)
  logging.debug(utility.run_shell_command("systemctl restart i2p-tbng").decode("utf-8"))
  logging.info("I2P Restart called")  

def i2p_stop(options):
  check_options(options,0)
  logging.debug(utility.run_shell_command("systemctl stop i2p-tbng").decode("utf-8"))
  logging.info("I2P Stop called")

def get_default_interface(options):
  check_options(options,0)
  interface_name=utility.run_piped(["ip","r","g","1.1.1.1"],["sed","-rn","s/^.*dev ([^ ]*).*$/\\1/p"])[0].decode("utf-8").strip()
  logging.debug("Return value: {0}".format(interface_name))
  interface_known=False
  for interface in configuration['wan_interface']:
    if interface['name'] == interface_name:
     interface_known=True
     break
  
  if interface_known:
    print(interface_name)
  else:
    raise Exception("Interface is unknown or not configured")


def set_default_interface(options):
  check_options(options,1)
  wan = []
  for i in configuration['wan_interface']:
     wan.append(i['name'])
  if options[0] not in wan:
    raise Exception("Interface not configured WAN interfaces list.")
  command=""  
  for i in wan:
    device_managed=is_managed(i)
    if device_managed:
      command += "nmcli dev disconnect {0}\n".format(i)
    else:
      command += "ifdown {0}\n".format(i)

  if is_managed(options[0]):
   command += "nmcli dev connect {0}\n".format(options[0])
  else:
   command += "ifup {0}\n".format(options[0]) 
 
  logging.debug(command)
  logging.debug(utility.run_shell_command(command).decode("utf-8"))
  logging.info("Set default interface {0} called".format(options[0]))

def probe_obfs(options):
  check_options(options,0)
  obfs_options = {}
  obfs_options['none']=""
  obfs3=probe_obfs_binary("obfs3")
  obfs4=probe_obfs_binary("obfs4")

  if obfs3:
    obfs_options['obfs3']=obfs3

  if obfs4:
    obfs_options['obfs4']=obfs4
  
  print(json.dumps(obfs_options))

def probe_obfs_binary(mode):
  retval=""
  if mode == "obfs3":
    try:
      retval = utility.run_shell_command("which obfsproxy").decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
      logging.debug(e.output)
  elif mode == "obfs4":
     try:
       retval = utility.run_shell_command("which obfs4proxy").decode("utf-8").strip()
     except subprocess.CalledProcessError as e:
       logging.debug(e.output)
  else:
    raise Exception("Unsupported bridge mode")

  return retval


def tor_bridge(options):
  config_section="_tor_bridges_"
  check_options(options,1)
  obfs_setting = json.loads(options[0])

  config_update="""UseBridges 1
"""

  if obfs_setting['mode'] not in ['none','obfs3','obfs4']:
    raise Exception("Invalid bridge mode {0} specified".format(obfs_setting['mode']))

  runtime['tor_bridges']={}
  runtime['tor_bridges']['mode']=obfs_setting['mode']
  runtime['tor_bridges']['bridges']=obfs_setting['bridges']
  utility.removeFileData(torrc,config_prefix,config_section)
  
  if not obfs_setting['mode']=='none':
    for obfs_string in obfs_setting['bridges']:
      if not obfs_string.startswith( obfs_setting['mode']):
        raise Exception("Invalid bridge setting applied")
      else:
        config_update += "Bridge "+obfs_string + "\n"
    
    config_update += "ClientTransportPlugin " + obfs_setting['mode'] + " exec " + probe_obfs_binary(obfs_setting['mode'])

    if obfs_setting['mode']=='obfs3':
      config_update += " --managed"
    config_update +="\n"
    utility.appendFileData(torrc,config_prefix,config_section,config_update)
  
  try:  
    tor_restart([])
    update_runtime()
  except subprocess.CalledProcessError as e:
    utility.removeFileData(torrc,config_prefix,config_section)
    runtime['tor_bridges']={}
    runtime['tor_bridges']['mode']="none"
    runtime['tor_bridges']['bridges']=[]
    update_runtime()
    tor_restart([])
    raise Exception("There was an error restarting TOR after bridge update. Bridge disabled, TOR restarted.")
  logging.info("TOR Bridge called") 

def tor_reset(options):
  check_options(options,0)
  tor_bridge(['{"mode": "none", "bridges": []}'])
  tor_exclude_exit(['[]'])
  logging.info("TOR Reset called")


def tor_exclude_exit(options):
  check_options(options,1)
  config_section="_tor_countries_exclude_"  
  #load country codes from country file
  torcountry_path = current_dir+"/../config/torcountry.json"
  with open(torcountry_path) as data_file:
    torcountry = json.load(data_file)
  logging.debug("TOR country codes  loaded from file {0}".format(torcountry_path))  
  #parse json input for list
  provided_countries = json.loads(options[0])

  #check, that provided countries are in country list
  if provided_countries:
    Found=False
    for country in provided_countries:
      Found=False
      for listed_country in torcountry:
        Found = (listed_country['code'] == country)
        if Found:
          break

    if not Found:
      raise Exception("Country code provided is not valid - update countries list or correct the argument")
  
  utility.removeFileData(torrc,config_prefix,config_section)

  if provided_countries:
    runtime['tor_excluded_countries']=provided_countries
    config_update = "ExcludeExitNodes "
    for country in provided_countries:
      config_update += "{"+country +"},"
    utility.appendFileData(torrc,config_prefix,config_section,config_update)
  else:
    runtime['tor_excluded_countries']=[]

  try:
    tor_restart([])
    update_runtime()
  except subprocess.CalledProcessError as e:
    utility.removeFileData(torrc,config_prefix,config_section)
    runtime['tor_excluded_countries']=[]
    update_runtime()
    tor_restart([])
    raise Exception("There was an error restarting TOR after country list update. Exit nodes ban disabled, TOR restarted.")
  logging.info("TOR Exclude exit called")
  
def get_cpu_temp(options):
  check_options(options,0)
  retval="Temperature monitoring not supported"
  
  if 'cputemp' in configuration:
    retval=run_plugin("cputemp",configuration['cputemp'])
  print("{0}".format(retval))

def macspoof_wan(options):
  check_options(options,1)
  interface={}
  interface['name']=options[0]
  interfaces=configuration['wan_interface']
  is_found=False
  for iface in interfaces:
    if iface['name']==interface['name']:
      is_found=True
      if ('macspoof' in iface):
        if 'parameters' in iface['macspoof'].keys():
          interface.update(iface['macspoof']['parameters'])
        run_plugin("macspoof",iface['macspoof']['method'],json.dumps(interface))
      else:
        raise Exception("Mac spoof plugin method is not defined for interface {0}".format(interface['name']))
  if not is_found:
   raise Exception("Interface {0} not found".format(interface['name']))
  logging.info("Called macspoof for interface {0}".format(interface['name']))  

def patch_nmcli(options):
  check_options(options,0)
  logging.debug(utility.run_shell_command("chmod u+s,a-w `which nmcli`").decode("utf-8"))
  logging.info("nmcli patch called")

def version(options):
  check_options(options,0)
  print(__version__)


def is_managed(interface):
  command="nmcli dev show {0}|grep unmanaged||true".format(interface)
  return "unmanaged" not in utility.run_shell_command(command).decode("utf-8") 
    
def is_wireless(section,name):
  interface_found=False
  logging.debug("is_wireless called with section: {0} and name: {1}".format(section,name)) 
  for interface in section:
    if interface['name']==name:
      interface_found=True                         
      if 'wireless' in interface and interface['wireless']:
        return True
  if not interface_found:
    raise Exception("Interface not found.")
  return False   

def update_runtime():
  with open(runtime_path, 'w') as outfile:
    json.dump(runtime, outfile)
  logging.debug("Runtime updated at {0}".format(runtime_path))
  logging.info("Runtime updated called")
 
# Standard boilerplate to call the main() function to begin
# the program.

if sys.version_info[0] < 3:
    raise Exception("Python 3.x is required.")

if not os.geteuid()==0:
 raise Exception("sudo or root is required.")

if __name__ == '__main__':
  parser = argparse.ArgumentParser( 
                                    description = "Commands executor for TBNG project.",
                                    epilog = "As an alternative to the commandline, params can be placed in a file, one per line, and specified on the commandline like '%(prog)s @params.conf'.",
                                    fromfile_prefix_chars = '@' )

  parser.add_argument(
                      "command",
                      help = "pass command to the program - use 'help' to see available options",
                      metavar = "command")

  parser.add_argument(
                      "options",
                      help = "pass command options to the program (optional)",
                      metavar = "options",
                      nargs = '*',
                      default = [])

 
  parser.add_argument(
                      "-v",
                      "--verbose",
                      help="increase output verbosity",
                      action="store_true")


  args = parser.parse_args()

  
  # Setup logging
  if args.verbose:
    loglevel = logging.DEBUG
  else:
    loglevel = logging.INFO

  
  main(args, loglevel)
