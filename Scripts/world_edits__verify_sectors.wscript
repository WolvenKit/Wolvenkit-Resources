import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

const files = [];
const addedSectorFiles = [];
const errorMessages = {};

for (let filename of wkit.GetProjectFiles('resources')) {
    // Logger.Success(filename);
    if (filename.split('.').pop() === "xl") {
        files.push(filename);
    }
}

let currentFile;

// loop over every file
for (let file in files) {
    Logger.Info(`Parsing resource file...${files[file]}`);
    currentFile = files[file];
    ParseFile(files[file]);
}

for (let file in addedSectorFiles) {
    wkit.DeleteFile(addedSectorFiles[file], 'archive');
}

function setErrorMessage(sectorPath, msg) {
    errorMessages[currentFile] = errorMessages[currentFile] || [];
    errorMessages[currentFile][sectorPath] = errorMessages[currentFile][sectorPath] || [];
    errorMessages[currentFile][sectorPath].push(msg);
}

Object.keys(errorMessages).forEach(key => {
    Logger.Error(key);
    Object.keys(errorMessages[key]).forEach(sectorName => {
        Logger.Warning(`${sectorName}`);
        errorMessages[key][sectorName].forEach(errorMessage => {
            Logger.Warning(`\t${errorMessage}`);
        });
    });
})

function GetSectorCr2W(relativePath) {
    let file;
    // Load project vesion if it exists, otherwise add to the project
    if (wkit.FileExistsInProject(relativePath)) {
        file = wkit.GetFileFromProject(relativePath, OpenAs.GameFile);
    }
    else {
        file = wkit.GetFileFromBase(relativePath);
        if (file === null) {
            Logger.Error(relativePath + " could not be found");
            return null;
        }
        wkit.SaveToProject(relativePath, file);
        addedSectorFiles.push(relativePath);
    }

    const json = wkit.GameFileToJson(file);
    
    if (!json) {
        Logger.Info(`Could not read ${relativePath}`);
        return null;
    }
    return TypeHelper.JsonParse(json);
}

function findPotentialMatch(sector, nodeData, nodes, nodeDataItem, removal) {
    // we can't match
    if (!removal["debugName"]) {
        return;
    }    
    
    // with sectors of more than 350 nodes, look 75 nodes in both directions 
    const indexOffset = nodeData.length <= 350 ? 50 : 75;
    
    const startIndex = Math.max(0, nodeDataItem["NodeIndex"] - indexOffset);
    const endIndex = Math.min(nodeData.length, nodeDataItem["NodeIndex"] + indexOffset);

    const debugString = removal["debugName"].split(",")[0].replace(/\.\d+/, '');
    
    for (let i = startIndex; i < endIndex; i++) {
        const nodeDataEntry = nodeData[i];
        const potentialNode = nodes[nodeDataItem["NodeIndex"]];
        if (!potentialNode || potentialNode["Data"]["$type"] !== removal["type"]) {
            continue;
        }
        const potentialNodeData = potentialNode["Data"];
        if (!!potentialNodeData["debugName"] && `${potentialNode["debugName"]}`.includes(debugString)) {
            setErrorMessage(sector["path"], `\t\tPotential match: ${i} (potentialNode["debugName"])`);
        }
        if (!!potentialNodeData["data"] && !!potentialNodeData["data"]["DepotPath"] && `${potentialNodeData["data"]["DepotPath"] }`.includes(debugString)) {
            setErrorMessage(sector["path"], `\t\tPotential match: ${i} (${potentialNodeData["data"]["DepotPath"]})`);
        }
    }
}

function CheckNodeTypes(sector, nodeData, nodes) {
    const sectorPath = sector["path"];
    const nodeRemovals = sector["nodeDeletions"];
    nodeRemovals.forEach((removal) => {
        const removalIdx = removal["index"];         
        const nodeDataItem = nodeData[removalIdx];
        
        const debugString = !removal["debugName"] ? "" : ` (${removal["debugName"]})`;
        
        const node = nodes[nodeDataItem["NodeIndex"]];
        const nodeType = node["Data"]["$type"];
        if (nodeType === removal["type"]) {
            return;
        }
        setErrorMessage(sectorPath, `#${removalIdx}${debugString}: expected ${removal["type"]}, but was ${nodeType}`);
        findPotentialMatch(sector, nodeData, nodes, nodeDataItem, removal);
    });
}

function ParseFile(filePath) {
    const fileContent = wkit.LoadFromResources(filePath);
    if (!fileContent) {
        Logger.Info(`Could not read ${filePath}`);
        return;
    }
    const json = TypeHelper.JsonParse(wkit.YamlToJson(fileContent));
    
    if (!json["streaming"] || !json["streaming"]["sectors"]) {
        return;
    }
    
    let sectors = json["streaming"]["sectors"];
    
    sectors.forEach((sector) => {
        const sectorPath = sector["path"];
        
        let sectorCr2w = GetSectorCr2W(sectorPath);
        if (!sectorCr2w) {
            return;
        }
        const nodeData = sectorCr2w["Data"]["RootChunk"]["nodeData"]["Data"];
        const nodes = sectorCr2w["Data"]["RootChunk"]["nodes"];
        const nodeDataIndexMap = {};        
        
        nodeData.forEach(node => {
            nodeDataIndexMap[node["NodeIndex"]] = nodes[node["NodeIndex"]];
        });        
        
        if (`${nodeData.length}` !== sector["expectedNodes"]) {
            setErrorMessage(sectorPath, `Expected ${sector["expectedNodes"]} nodes, found ${nodeData.length}`);
        }
        
        CheckNodeTypes(sector, nodeData, nodeDataIndexMap);
    });    
    
    // Logger.Success(sectors);
}