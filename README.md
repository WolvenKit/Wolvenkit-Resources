# Wolvenkit-Resources
This is the **resource depot** for Wolvenkit. It hosts our shared scripts and plugins.

# How to install
You should never have to do this manually. You can install plugins from [inside Wolvenkit](https://wiki.redmodding.org/wolvenkit/wolvenkit-app/home/home-plugins), and scripts will automatically be synced every time you start the program.

However, if you are stuck behind a proxy or firewall, or if the download fails for any other reasons, here are instructions on how to install by hand:

## Manual install instructions

### Registering installed plugins
Whenever you install a plugin by hand, make sure to update the following file:  
`Cyberpunk 2077\tools\wolvenkit_plugins.json`  

The full list of plugin keys for the file is as follows:

| Plugin name                                                                                                         | Plugin key for .json |
|---------------------------------------------------------------------------------------------------------------------|:--------------------:|
| [CET](https://www.nexusmods.com/cyberpunk2077/mods/107)                                                             |   cyberengintweaks   |
| [Redscript](https://www.nexusmods.com/cyberpunk2077/mods/1511)                                                      |      redscript       |
| [MLSetupBuilder](https://github.com/Neurolinked/MlsetupBuilder/releases/)                                           |    mlsetupbuilder    |
| Wolvenkit Resources                                                                                                 | wolvenkit_resources  |
| Redmod                                                                                                              |        redmod        |
| [Red4EXT](https://www.nexusmods.com/cyberpunk2077/mods/2380)                                                        |       red4ext        |
| [TweakXL](https://www.nexusmods.com/cyberpunk2077/mods/4197)                                                        |       tweakXL        |
| [RedHotTools](https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-creators-theory/modding-tools/redhottools) |     redhottools      |

The rest of the section includes instructions on how to manually install and register the individual plugins.

### Wolvenkit Resources

1. Download [red.kark](https://github.com/WolvenKit/Wolvenkit-Resources/blob/main/red.kark) and put it into your game directory into the following path:   
`Cyberpunk 2077\tools\wolvenkit\wolvenkit-resources\red.kark`
2. Update `wolvenkit_plugins.json` with the following information (adjust as necessary):
```json
  "wolvenkit_resources": {
    "Id": 3,
    "Version": "X.X.X",
    "Files": [
      "C:\\Games\\Cyberpunk 2077\\tools\\wolvenkit\\wolvenkit-resources\\red.kark",
      "C:\\Users\\YOURUSERNAME\\AppData\\Roaming\\REDModding\\WolvenKit\\red.db"
    ]
  },
```
3. Adjust "ID" to be one higher than the ID of the last plugin in the list (they're numbered consecutively)
4. Adjust "Version" to the [last release version](https://github.com/WolvenKit/Wolvenkit-Resources/releases/) of the Wolvenkit Resources repository
5. Replace "C:\\Games\\Cyberpunk 2077" with the path to your actual game install. Mind the double slashes!
6. Replace "YOURUSERNAME" with your actual Windows username

### MLSetupBuilder
1. You can find manual install instructions on the [wiki](https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-creators-theory/modding-tools/mlsetup-builder#installation), simply expand the "manual install" box.
2. To register MLSB as a plugin in Wolvenkit, update `wolvenkit_plugins.json` with the following information (adjust as necessary):
```json
  "mlsetupbuilder": {
    "Id": 2,
    "Version": "X.X.X",
    "Files": [
        ...
    ]
  },
```
3. For updating, the list "Files" should hold the absolut paths of every file inside the mlsb directory, no matter how deeply it's nested. Mind the double slashes!  
Alternatively, you can leave it empty.


