// @author spirit
// @version 1.1
// @description
// It is recommended to use VolumetricSelection2077 (v1000.0.0-beta8+) or RedHotTools (v1.3.0-beta.7+) as both offer a more refined, precise and easier way of removing occlusion nodes.
// This script generates an .xl file that removes all occluder nodes from all sectors in the project. 
// Does not include occlusion that is caused by collision nodes.
// Special thanks to Simarilius for helping with the foundation of this script.
// @usage
// Detailed instructions can be found in the wiki.
// 1. Indentify all sectors that add occluder nodes using RedHotTools
// 2. Add all affected sectors to a new project
// 3. Run the script
// 4. Move the generated file into your archive mod folder

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

let RemoverStr = "streaming:\n  sectors:\n"
let sectorNames = "NoOccl_"
let sectors = []
let removedNodesCount = 0
let removedSectorCount = 0

// Gets FileName only from path
function getFileNameWithoutExt(filePath) {
  const fileNameWithExt = filePath.split("\\").pop(); // Get last segment
  const ext = fileNameWithExt.lastIndexOf('.');
  return ext === -1 ? fileNameWithExt : fileNameWithExt.slice(0, ext); // Remove extension
}

// generates a shortened sector name 
function shortenSectorName(sectorName) {
  let shortSectorName = ""
  let sectorNameArray = sectorName.split("_")
  if (sectorNameArray[0] == "exterior") {
    shortSectorName += "e"
  } else if (sectorNameArray[0] == "interior") {
    shortSectorName += "i"
  } else {
    Logger.warn("Error while shortening sector name, unexpected sector type!")
  }
  shortSectorName += sectorNameArray[1]+sectorNameArray[2]+sectorNameArray[3]+sectorNameArray[4]+"_"
  return shortSectorName
}
// Lists all streamingsectors in Projects 
for (let filename of wkit.GetProjectFiles('archive')) {
    if (filename.split('.').pop() === "streamingsector") {
        sectors.push(filename);
    }
}
// Goes through all streamingsectors 
for (const fileName of sectors) {
  removedSectorCount += 1
  let node_data_indexs=[]
  if (wkit.FileExistsInProject(fileName)) {
      var file = wkit.GetFileFromProject(fileName, OpenAs.GameFile);
    } else {
        file = wkit.GetFileFromBase(fileName);
    }
      var json = TypeHelper.JsonParse(wkit.GameFileToJson(file));
    let nodeData = json["Data"]["RootChunk"]["nodeData"]["Data"]
    // Generates the Path and expected Nodes section 
    RemoverStr += "    - path: "+fileName+"\n"+"      expectedNodes: "+nodeData.length.toString()+"\n"+"      nodeDeletions:"+"\n";
    sectorNames += ""+shortenSectorName(getFileNameWithoutExt(fileName));

    Logger.Info('Identifying Occulder Nodes in '+fileName)
     let nodes = json["Data"]["RootChunk"]["nodes"];
    
     // Finds all Occluders in nodes
    nodes.forEach((nodeInst, index) => {
     if (nodeInst["Data"]["$type"] !== null ) {
     if ( nodeInst["Data"]["$type"].includes("Occluder"))  {
     node_data_indexs.push({"index":index.toString(), "type":nodeInst["Data"]["$type"]})
       }
      }
     });
     // Gets Index of nodeData and nodeType from nodes
     for (let index in nodeData) {
      for (let index2 in node_data_indexs) {
        if (nodeData[index]["NodeIndex"]==node_data_indexs[index2]["index"]) {
          RemoverStr += "        - index: "+index+"\n          type: "+node_data_indexs[index2]["type"]+"\n";
          removedNodesCount += 1;
        }
      }
     }
     
} 
// Saves the File to Resources
wkit.SaveToResources(sectorNames+".xl", RemoverStr);
Logger.Info("Saved "+sectorNames+".xl to resources!");
Logger.Info("Removed "+removedNodesCount+" nodes from "+removedSectorCount+" sectors!")
