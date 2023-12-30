import * as Logger from 'Internal/Logger.wscript';
import * as TypeHelper from 'Internal/TypeHelper.wscript';

let currentMeshRelativePath;
let currentMesh;

function loadCurrentMesh() {
    const activeDocument = wkit.GetActiveDocument(); 
    let absolutePath = activeDocument?.FilePath;
    if (!absolutePath || !absolutePath.endsWith('.mesh')) {
        Logger.Error(`Please run from scripts menu with a .mesh file open!`);
    }    
    
    currentMeshRelativePath = absolutePath.split('archive\\').pop();
    if (!currentMeshRelativePath || !wkit.FileExists(currentMeshRelativePath)) {
        Logger.Error(`No open mesh file found. Please switch to your currently-active mesh and run this script from the menu!`);
        return null;
    }
    
    try {
        const fileContent = wkit.LoadGameFileFromProject(currentMeshRelativePath, 'json');
        return TypeHelper.JsonParse(fileContent);
    } catch (err) {
        Logger.Error(`failed to parse mesh file at ${currentMeshRelativePath}. Make sure the path is correct.`);
    }
    return null;    
}


export function run() {
    currentMesh = loadCurrentMesh();
    
    if (!currentMesh || !currentMesh["Data"]["RootChunk"]) return;

    let appearances = [];
    try {
        appearances = currentMesh["Data"]["RootChunk"]["appearances"];
        const appearanceNames = appearances.map((appearance) => appearance["Data"]["name"]["value"]);
        Logger.Info(`\n${appearanceNames.join('\n')}`);
    } catch (err) {
        Logger.Error('failed to parse mesh');
    }    
}