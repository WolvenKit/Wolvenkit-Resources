import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

/* ========================================================================
 * Set this to "false" to skip check for debug name
 * ======================================================================== */
const checkByNodeName = true;


const files = [];
const addedSectorFiles = [];
const errorMessages = {};

for (let filename of wkit.GetProjectFiles('resources')) {
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

// helper function to turn something like this
// 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160
// into this
// 143-160
function groupNumbersInRanges(numbers) {
    if (!numbers || numbers.length === 0) {
        return [];
    }

    numbers.sort((a, b) => a - b);
    const ranges = [];
    let start = numbers[0];
    let end = start;

    for (let i = 1; i < numbers.length; i++) {
        if (numbers[i] === end + 1) {
            end = numbers[i];
        } else {
            ranges.push(start === end ? `${start}` : `${start}-${end}`);
            start = numbers[i];
            end = start;
        }
    }

    ranges.push(start === end ? `${start}` : `${start}-${end}`);
    return ranges.join(", ");
}

function getFromDepotPath(potentialNodeData, jsonKey) {
    if (!potentialNodeData || !potentialNodeData[jsonKey] || !potentialNodeData[jsonKey]["DepotPath"]) {
        return null;
    }
    const depotPath = potentialNodeData[jsonKey]["DepotPath"];
    if (!!depotPath["value"]) {
        return depotPath["value"];
    } 
    return depotPath;
}

function getNodeDescriptorString(potentialNodeData) {
    if (!potentialNodeData) {
        return '';
    }
    let ret = [];
    
    if (!potentialNodeData["debugName"]) {
        ret.push(potentialNodeData["Name"]);
    }

    const depotPathProperties = ["data", "entityTemplate", "mesh", "particleSystem", "probeDataRef", "fracturingEffect"];
    for (let i = 0; i < depotPathProperties.length; i++) {
        const depotPath = getFromDepotPath(potentialNodeData, depotPathProperties[i]);
        if (!!depotPath) {
            ret.push(depotPath.split("\\").pop());
            break;
        }
    }
        
    return ret.join(', ');
}

function resolveDebugName(removal) {
    const debugName = removal["debugName"];
    if (!debugName) {
        return;
    }
    return debugName
        .replace(/\.\d+/g, '') // strip numeric file types
        .replace('_default', '') // strip _default suffix
        .split(",")[0] // if it's a list: take the first item
        .split(" ")[0] // if it contains spaces: take the first item
        .split(".")[0]; // if it contains dots (e.g. file extensions): take the first item
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

    const debugString = removal["debugName"].split(",")[0].split(".")[0].replace(/\.\d+/, '');
    
    const potentialMatches = {};
    
    for (let i = startIndex; i < endIndex; i++) {
        const nodeDataEntry = nodeData[i];
        const potentialNode = nodes[nodeDataItem["NodeIndex"]];
        if (!potentialNode || potentialNode["Data"]["$type"] !== removal["type"]) {
            continue;
        }
        const nodeDescriptorString = getNodeDescriptorString(potentialNode["Data"]);
        if (!nodeDescriptorString || !nodeDescriptorString.includes(debugString)) {
            continue;
        }
        potentialMatches[nodeDescriptorString] ||= [];
        potentialMatches[nodeDescriptorString].push(i);
    }
    if (Object.keys(potentialMatches).length === 0) {
        return;
    } 
    Object.keys(potentialMatches).forEach(key => {    
        setErrorMessage(sector["path"], `\t\t\Potential replacements: ${key} (${groupNumbersInRanges(potentialMatches[key])})`);        
    })
}

function CheckNodeTypes(sector, nodeData, nodes) {
    const sectorPath = sector["path"];
    const nodeRemovals = sector["nodeDeletions"];
    nodeRemovals.forEach((removal) => {
        const removalIdx = removal["index"];         
        const nodeDataItem = nodeData[removalIdx];
        
        const node = nodes[nodeDataItem["NodeIndex"]];
        const nodeType = node["Data"]["$type"];

        const debugString = resolveDebugName(removal);
        
        const nodeDescriptorString = getNodeDescriptorString(node["Data"]);
        
        if (nodeType === removal["type"]) {
            // If we can't compare by string, it's okay
            if (!checkByNodeName || !debugString || !nodeDescriptorString || nodeDescriptorString.includes(debugString)) {
                return;                
            }
            // we can compare by string, and they don't match
            setErrorMessage(sectorPath, `#${removalIdx} (${debugString}): nodes[${nodeDataItem["NodeIndex"]}] seems to point at something else (${nodeDescriptorString})`);
        } else {
            // types are not equal
            setErrorMessage(sectorPath, `#${removalIdx} (${debugString}): expected ${removal["type"]}, but was ${nodeType}`);
        }
        
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
}