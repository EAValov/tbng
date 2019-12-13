//globals

  var path = require('path');   
  var util = require('util');
  var engine = path.join(__dirname,'../../engine/tbng.py');
  var engineRun = "sudo "+engine;
  var config_path=path.join(__dirname,'../../config/tbng.json');
  var runtime_path=path.join(__dirname,'../../config/runtime.json');
  var torcountry_path=path.join(__dirname,'../../config/torcountry.json');
  var config=require(config_path);
  


this.readStatus = function()
{
   var fs = require('fs');
   if (fs.existsSync(runtime_path)) { 
     return JSON.parse(fs.readFileSync(runtime_path, 'utf8')).mode.toUpperCase();
   }
   else
   {
     return "DIRECT";
   }

}

this.switchMode = function(modeNew)
{
   
   var execSync = require('child_process').execSync;
   script = execSync(engineRun+" mode "+modeNew.toLowerCase());
   console.log("Called switchMode with parameter: ",modeNew);
   return script
   
  
}

this.changePassword = function(oldPass,newPass,confirmPass)
{
   path = require('path');   
   var pathToPass =path.join(__dirname,'../../config/user.json');
   var user=require(pathToPass);
   if (oldPass!=user.password)
   {
      throw "Wrong password!";
   }
   
   if (!isAscii(newPass))
   {
      throw "Password should contain only ASCII symbols"
   }

   if (newPass!=confirmPass)
   {
      throw "Passwords do not match!";
   }
   
   user.password=newPass;
   var fs = require('fs');
   var toFile = JSON.stringify(user);
   console.log(user);
   fs.truncateSync(pathToPass,0);
   fs.writeFileSync(pathToPass,toFile,"UTF-8",{'flags': 'w+'});    
    
}

this.reboot = function()
{
   
   var execSync = require('child_process').execSync;
   var reboot = execSync(engineRun+" reboot");
   console.log("Called reboot...");
     
}

this.shutdown = function()
{
   
   var execSync = require('child_process').execSync;
   var shutdown = execSync(engineRun+" shutdown");
   console.log("Called shutdown...");
     
}

this.halt = function()
{
  var execSync = require('child_process').execSync;
  var shutdown = execSync(engineRun+" halt");
  console.log("Called halt...");
}

this.sysInfo = function()
{

  var os = require('os');
  var ifaces = os.networkInterfaces();
  var interfaces=[];
  
 //collecting interfaces
 Object.keys(ifaces).forEach(function (ifname) {
  

  ifaces[ifname].forEach(function (iface) {
    if ('IPv4' !== iface.family || iface.internal !== false) {
      // skip over internal (i.e. 127.0.0.1) and non-ipv4 addresses
      return;
    }
      var single_interface = 
      {
       name:ifname,
       address:iface.address,
       netmask:iface.netmask,
       mac:iface.mac,
      }
      interfaces.push(single_interface);  
   });
 });


 var temperature = "Not supported ";
 
 try
  {
    var execSync = require('child_process').execSync;
    res = execSync(engineRun+" get_cpu_temp").toString().split("\n")[0];
    console.log(res);
    temperature = res; 
  }
  catch(error)
  {
    console.log("Dump of stderr:")
    console.log(error.toString());
  }
  
 var system_info = {
   
 network : interfaces,
 ram : os.freemem()/1024,
 systemLoad : os.loadavg(),
 hostName : os.hostname(),
 platform : os.platform(),
 arch : os.arch(),
 release: os.release(),
 cpuCount : os.cpus().length,
 cpuTemp : temperature
  
 };
 
 
 return system_info;

}

function isAscii(text)
{
  var ascii=/^[ -~\t\n\r]+$/;
  
  if(ascii.test(text))
    return true;
  
  return false;
}

function doesExist(path) {
  var fs=require('fs');
  try {
    fs.statSync(path)
    return true
  } catch(err) {
    return !(err && err.code === 'ENOENT');
  }
}

this.i2pAction = function(i2p)
{

   var execSync = require('child_process').execSync;
   script = execSync(engineRun +" i2p_"+i2p.toLowerCase());
   return "Command successfully passed to system";

}

this.torAction= function(tor)
{
   var execSync = require('child_process').execSync;
   script = execSync(engineRun +" tor_"+tor.toLowerCase());
   return "Command successfully passed to system";
}

  
this.wifi = function()
{
   
 //Checking first available wifi interface
 var retVal=null
 if (config.wan_interface && util.isArray(config.wan_interface))
 {
  config.wan_interface.forEach(function(interface){
      if (interface.wireless)
      {
         var wifi = require('node-wifi');
     
         var settings = {
           debug: true,
           iface: interface.name,
           connectionTimeout: 20000
         };
        //wifi.configure(settings);
        wifi.init(settings); 
        retVal=wifi;
        return; 
      }      
    }); 
 }
   return retVal;     
}  


this.getWanInterfaces = function()
{
   
   interface_list=[];
  //getting active interface
  strActiveInterface="";
  var execSync = require('child_process').execSync
  try
  {
    res = execSync(engineRun+" get_default_interface").toString().split("\n")[0];
    console.log(res);
    strActiveInterface = res; 
  }
  catch(error)
  {
    console.log("Dump of stderr:")
    console.log(error.toString());
  }
 
 if (config.wan_interface && util.isArray(config.wan_interface))
 {
  config.wan_interface.forEach(function(interface){
     someinterface={};
     someinterface.name=interface.name;
     someinterface.current=false;

     if(interface.wireless)
       someinterface.wireless=true
     else
       someinterface.wireless=false

     if(someinterface.name==strActiveInterface)
     {
        someinterface.current=true;
     }
     
     interface_list.push(someinterface);
  });
 }
   console.log("Acquired interface list:")
   console.log(interface_list);
   return interface_list;
}

this.setDefaultInterface = function(interface)
{
   var execSync = require('child_process').execSync;
   execSync(engineRun+" set_default_interface "+interface);
}

this.getObfsModes = function()
{
  var available_modes={};
  //get supported obfs modes
  try
  {
    var execSync = require('child_process').execSync;
    res = execSync(engineRun+" probe_obfs").toString().split("\n")[0];
    console.log(res);
    available_modes=Object.keys(JSON.parse(res));
  }
  catch(error)
  {
    console.log("Dump of stderr:")
    console.log(error.toString());
  }   
  
  var modes= [];
  var defaultMode = {};
  available_modes.forEach(function(single_mode) {
  var Mode = {};
  Mode.name=single_mode;
  Mode.bridges=[];
  Mode.current=false;
  modes.push(Mode);
  });


  //now loading from runtime
  var fs = require('fs');
  var current_mode={};
  
  if (fs.existsSync(runtime_path)) current_mode=JSON.parse(fs.readFileSync(runtime_path, 'utf8')).tor_bridges;
 
    modes.forEach(function(mode, i,mod) {
       if (current_mode)
       {
         if (mode.name == current_mode.mode)
         {
           mod[i].current=true;
           mod[i].bridges = current_mode.bridges;
         }
       } else
       {
          if(mode.name == "none") mod[i].current=false;
       }
      
     });
  console.log(modes);
  return modes;
}

this.setObfsMode=function(obfs_mode)
{
  argument="'"+JSON.stringify(obfs_mode)+"'";
  var execSync = require('child_process').execSync;
  res = execSync(engineRun+" tor_bridge "+argument).toString().split("\n")[0];
  console.log(res);   
}

this.resetTOR=function()
{
  var execSync = require('child_process').execSync;
  res = execSync(engineRun+" tor_reset").toString().split("\n")[0];
  console.log(res);
}

this.getCountryList = function()
{
   var fs = require('fs');
   tor_country=[];
   selected_countries=[];
   if (fs.existsSync(torcountry_path)) {
     tor_country=JSON.parse(fs.readFileSync(torcountry_path, 'utf8'));
   }
   else
   {
     throw new Error("No TOR country list found. Unrecoverable.");
   }
   
   if (fs.existsSync(runtime_path)) {
     selected_countries=JSON.parse(fs.readFileSync(runtime_path, 'utf8')).tor_excluded_countries;
   }


   countries=[];
   
   tor_country.forEach(function(country) {
     someCountry={};
     someCountry.code=country.code;
     someCountry.name=country.name;
     someCountry.selected=false;
     selected_countries.forEach(function(selected) {
       if (someCountry.code==selected)
         someCountry.selected=true;
     });
     countries.push(someCountry);
   });   
  
   return countries;
}

this.setExitNodes = function(countries)
{
  argument="'"+JSON.stringify(countries)+"'";
  var execSync = require('child_process').execSync;
  res = execSync(engineRun+" tor_exclude_exit "+argument).toString().split("\n")[0];
  console.log(res);
}

this.spoofInterface = function(interface)
{
  var execSync = require('child_process').execSync;
  res = execSync(engineRun+" macspoof_wan "+interface).toString().split("\n")[0];
  console.log(res);
}

this.restartDNSMasq = function()
{
  var execSync = require('child_process').execSync;
  execSync(engineRun+" dnsmasq_restart").toString().split("\n")[0];
  return "Command successfully passed to system";
}
