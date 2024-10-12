// Geneates .xl file that removes all occlusion meshes from all streamingsectors in the project
// Special thanks to simarilius for writing most of the code
// @author spirit
// @version 1.0

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

let RemoverStr = "streaming:\n  sectors:\n"
let sectorNames = "OcclusionRemover_"
let sectors = []

// Gets FileName only from path
function getFileNameWithoutExt(filePath) {
  const fileNameWithExt = filePath.split("\\").pop(); // Get last segment
  const ext = fileNameWithExt.lastIndexOf('.');
  return ext === -1 ? fileNameWithExt : fileNameWithExt.slice(0, ext); // Remove extension
}
// Lists all streamingsectors in Projects 
for (let filename of wkit.GetProjectFiles('archive')) {
    if (filename.split('.').pop() === "streamingsector") {
        sectors.push(filename);
    }
}
// Goes through all streamingsectors 
for (const fileName of sectors) {

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
    sectorNames += ""+getFileNameWithoutExt(fileName);

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
        }
      }
     }
     
} 
// Saves the File to Resources
wkit.SaveToResources(sectorNames+".xl", RemoverStr);
Logger.Info("Saved "+sectorNames+".xl to resources!");
