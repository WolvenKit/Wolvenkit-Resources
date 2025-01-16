import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

// @author manavortex
// @version 1.0
// @description Run this script to update all .xl node removals in your project after a patch. Set the properties below if you don't want automatic changes.

/* ========================================================================
 * Set this to "false" to skip check for debug name
 * ======================================================================== */
const checkByNodeName = true;
const removeNodesWithoutMatch = true;


const files = [];
const addedSectorFiles = [];
const errorMessages = {};

for (let filename of wkit.GetProjectFiles('resources')) {
    if (filename.split('.').pop() === "xl") {
        files.push(filename);
    }
}

let currentFile;
let writeFile = false;
let nodeIndicesToRemove = [];

// loop over every file

try {
    for (let file in files) {
        Logger.Info(`Parsing resource file...${files[file]}`);
        currentFile = files[file];
        ParseFile(files[file]);
    }    
} catch (Error e) {
    Logger.Error(e);
    Logger.Error("");
    Logger.Error(`Something went wrong! Make sure to update Wolvenkit (install latest Nightly!)`);
    Logger.Error(`If that does not help, please get in touch!`);
    return;
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

function getFromDepotPath(potentialNodeData, jsonKey) {
    if (!potentialNodeData || !potentialNodeData[jsonKey] || !potentialNodeData[jsonKey]["DepotPath"]) {
        return null;
    }
    const depotPath = potentialNodeData[jsonKey]["DepotPath"];
    if (!!depotPath["value"]) {
        return depotPath["value"];
    } 
    return '';
}

function getNodeDescriptorString(potentialNodeData) {
    if (!potentialNodeData) {
        return '';
    }
    let ret = [];
    
    if (!potentialNodeData["debugName"]) {
        ret.push(potentialNodeData["debugName"]);
    }

    const depotPathProperties = ["mesh", "entityTemplate", "material", "data", "particleSystem", "probeDataRef", "fracturingEffect"];
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
        .split('\\').pop() // if it's a file path: Take only file name
        .split(",")[0] // if it's a list: take the first item
        .split(" ")[0] // if it contains spaces: take the first item
        .split(".")[0]; // if it contains dots (e.g. file extensions): take the first item
}

// find potentially matching nodes in the list. Factor out as a function so we can run it twice, 
// once with a limited search, and once with the full list. 
function findPotentialMatches(removal, nodeData, nodes, debugString, startIndex, endIndex) {   
    const potentialMatches = [];
    for (let i = startIndex; i < endIndex; i++) {
        const nodeDataEntry = nodeData[i];
        const potentialNode = nodes[nodeDataEntry["NodeIndex"]];

        if (!potentialNode || potentialNode["Data"]["$type"] !== removal["type"]) {
            continue;
        }
        const nodeDescriptorString = getNodeDescriptorString(potentialNode["Data"]);
        if (!nodeDescriptorString || nodeDescriptorString !== debugString) {
            continue;
        }
        potentialMatches[nodeDescriptorString] ||= [];
        potentialMatches[nodeDescriptorString].push(i);
    }
    return potentialMatches;
}
function findPotentialMatch(sector, nodeData, nodes, nodeDataItem, removal) {
    const debugString = resolveDebugName(removal);
    
    // we can't match
    if (!debugString) {
        return;
    }    
    
    const startIndex = Math.max(0, nodeDataItem["NodeIndex"] - trunc(nodeData.length / 6));
    const endIndex = Math.min(nodeData.length, nodeDataItem["NodeIndex"] + trunc(nodeData.length / 6));
    
    let potentialMatches = findPotentialMatches(removal, nodeData, nodes, debugString, startIndex, endIndex);      
   
    // if we found no matches, search the whole array
    if (Object.keys(potentialMatches).length === 0) {
        potentialMatches = findPotentialMatches(removal, nodeData, nodes, debugString, 0, nodeData.length -1);
    } 
    
    // if we still found no matches, then the entry should be dropped
    if (Object.keys(potentialMatches).length === 0) {
        nodeIndicesToRemove.push(removal["index"]);
        writeFile = true;
        return;
    } 
    
    if (Object.keys(potentialMatches).length === 1) {
        let values = potentialMatches[Object.keys(potentialMatches)[0]];
        // if we have more than one match, check if we have an offset of 1
        if (values.length > 1) {
            values = values.filter(v => v === removal["index"] -1 || v === removal["index"] +1);
        }
        if (values.length === 1) {
            removal["index"] = values[0];
            writeFile = true;
            return;
        }
    } 
    Object.keys(potentialMatches).forEach(key => {    
        setErrorMessage(sector["path"], `\t\t\Potential replacements: ${key} (${potentialMatches[key].join(", ")})`);        
    })
}

function CheckNodeValidity(sector, nodeData, nodes) {
    const sectorPath = sector["path"];
    const nodeRemovals = sector["nodeDeletions"];
    nodeRemovals.forEach((removal) => {
        const removalIdx = removal["index"];         
        const nodeDataItem = nodeData[removalIdx];
        if (!nodeDataItem) {
            setErrorMessage(sectorPath, `#${removalIdx}: No node data item found!`);
            return;
        }
        
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
            setErrorMessage(sectorPath, `#${removalIdx} (${debugString}): mod wants ${removal["type"]}, but it is a ${nodeType}`);
        }
        
        findPotentialMatch(sector, nodeData, nodes, nodeDataItem, removal);
    });
}

function ParseFile(filePath) {
    let fileContent = wkit.LoadFromResources(filePath);
    if (!fileContent) {
        Logger.Info(`Could not read ${filePath}`);
        return;
    }
    const json = TypeHelper.JsonParse(wkit.YamlToJson(fileContent));
    
    if (!json["streaming"] || !json["streaming"]["sectors"]) {
        return;
    }
    
    let sectors = json["streaming"]["sectors"];

    nodeIndicesToRemove = [];
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
        
        CheckNodeValidity(sector, nodeData, nodeDataIndexMap);
    });

    if (!writeFile) {
        return;
    }

    // remove "dead" node removals, then sort by index
    sectors.forEach((sector) => {
        sector["nodeDeletions"] = sector["nodeDeletions"]
            .filter(removal => !removeNodesWithoutMatch || !nodeIndicesToRemove.find(i => i === removal["index"]))
            .sort((a, b) => a["index"] - b["index"]);
    });
    
    wkit.SaveToResources(filePath, wkit.JsonToYaml(TypeHelper.JsonStringify(json)));
}