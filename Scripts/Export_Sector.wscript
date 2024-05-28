// Exports StreamingSector files and all referenced files (recursively)
// @author Simarilius, DZK, Seberoth & manavortex
// @version 1.8
// Requires 8.14 or higher
import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';
import * as Collision_Shapes from 'collision_shapes.wscript';

// Export all sectors in project? (set to false to only use sectors list below)
const add_from_project = true;

// Set to true to disable warnings about failed meshes
const suppressLogFileOutput = false;

// If you dont want mats then set this to false
const withmats=true;

// If you only want files that are new exporting set this to true
const only_new=true

// If you want mesh colliders extracting then set this to true
const mesh_colliders=false

// format for images to get exported to
const imgFormat = 'png'

/**
 * Any sectors in the list below will be added to your project before exporting. List of sector files to add to your project, see wiki: https://tinyurl.com/cyberpunk2077worldsectors
 *
 * If the file is in default _compiled dir, file name is enough. Otherwise, put the full path (remember to double slashes)!
 */
let sectors = [
	// El Coyote
	//'interior_-20_-16_0_1','interior_-39_-31_0_0','interior_-39_-32_0_0','interior_-40_-31_0_0','interior_-40_-32_0_0'
    
    /* V's apartment: H10 */
    // 'interior_-22_19_1_1', 'interior_-22_20_1_1', 'interior_-43_39_3_0', 'interior_-44_39_3_0', 'interior_-44_40_3_0', 'interior_-46_40_3_0', 'exterior_-22_19_1_0', 'quest_b705140105a75f58', 'quest_acd280b2b73c4d5b', 'quest_2467054678ccf8f6', 'quest_3509076113f76078', 'quest_e1ef450702659584', 'quest_2be595b225125038', 'quest_5eb84e72f3942283', 'quest_e1ef450702659584', 'quest_1fbb2ceaeeaac973',

    /* V's apartment: Loft */
    // 'exterior_-24_-16_1_0', 'interior_-24_-16_1_1', 'interior_-48_-31_2_0', 'quest_ca115e9713d725d7'

    /* V's apartment: Northside dump */
    // 'exterior_-24_34_0_0', 'interior_-48_68_0_0', 'interior_-12_17_0_2', 'exterior_-12_17_0_1', 'interior_-47_69_0_0', 'interior_-48_69_0_0',

    /* V's apartment: Corpo Plaza */
    // 'interior_-25_5_0_1', 'interior_-51_10_1_0', 'interior_-51_11_1_0', 'interior_-50_11_1_0', 'interior_-26_5_0_1',

    /* V's penthouse */
    // 'exterior_-21_18_1_0', 'interior_-11_9_0_2', 'interior_-21_18_1_1', 'interior_-22_18_1_1 ', 'interior_-43_37_3_0 ', 'interior_-43_39_3_0', 'quest_81387f43768bad6c',   

    /* V's Japantown Apartment */
    // 'interior_-13_15_0_0', 'interior_-13_15_0_1', 'interior_-25_30_0_0',  
 
    /* V's Dogtown apartment */
    // 'ep1\\interior_-70_-81_2_0', 'ep1\\exterior_-35_-40_1_0', 'ep1\\exterior_-35_-41_1_0', 'ep1\\exterior_-18_-21_0_1', 'ep1\\interior_-70_-80_2_0'    
];

/*
 * ===================================== Change below this line at own risk ========================================
 */
 
 

const fileTemplate = '{"Header":{"WKitJsonVersion":"0.0.7","DataType":"CR2W"},"Data":{"Version":195,"BuildVersion":0,"RootChunk":{},"EmbeddedFiles":[]}}';

let jsonExtensions = [".app", ".ent", ".mi", ".mt", ".streamingsector",".cfoliage"];
let exportExtensions = [".mesh",".w2mesh",".physicalscene",".xbm"]; // need xbms for decals
let exportEmbeddedExtensions = [".mesh",".w2mesh", ".xbm", ".mlmask", ".mlsetup",".cfoliage", ".streamingsector"];

if (!withmats){
	Logger.Info('Withmats false')
    jsonExtensions = [".app", ".ent", ".streamingsector",".cfoliage"];
    exportExtensions = [".mesh",".w2mesh",".physicalscene"];
    exportEmbeddedExtensions = [".mesh",".w2mesh",".cfoliage", ".streamingsector"];
}

const sectorPathInFiles = 'base\\worlds\\03_night_city\\_compiled\\default';
for (let i = 0; i < sectors.length; i += 1) {
    let sectorPath = sectors[i];
    if ((sectorPath.match(/\/\//g) || []).length < 2) {    // one double slash is ok (for PL sectors)
        sectorPath = `${sectorPathInFiles}\\${sectorPath}`;
    }
    if (!sectorPath.endsWith('.streamingsector')) {
        sectorPath = `${sectorPath}.streamingsector`;
    }
    sectors[i] = sectorPath;
}

if (add_from_project) {
    for (let filename of wkit.GetProjectFiles('archive')) {
        // Logger.Success(filename);
        if (filename.split('.').pop() === "streamingsector") {
            sectors.push(filename);
        }
    }

    // now remove duplicates
    sectors = Array.from(new Set(sectors));
}

// sets of files that are parsed for processing
const parsedFiles = new Set();
const projectSet = new Set();
const exportSet = new Set();
const jsonSet = new Set();

// loop over every sector in `sectors`
for (let sect in sectors) {
    Logger.Info(`Parsing sector...\n${sectors[sect]}`);
    ParseFile(sectors[sect], null);
}

// save all our files to the project
Logger.Info(`Exporting ${projectSet.size} files to JSON. This might take a while...`);
for (const fileName of projectSet) {
    let file;
    if (wkit.FileExistsInProject(fileName)) {
        file = wkit.GetFileFromProject(fileName, OpenAs.GameFile);
    } else {
        file = wkit.GetFileFromBase(fileName);
        wkit.SaveToProject(fileName, file);
    }
    if (!!file && jsonSet.has(fileName) && jsonExtensions.includes(file.Extension)) {
        const path = wkit.ChangeExtension(file.Name, `${file.Extension}.json`);
        const json = wkit.GameFileToJson(file);
        wkit.SaveToRaw(path, json);
    }
}

let exportsettings = {Mesh: { ExportType: "MeshOnly", WithMaterials: withmats, ImageType: imgFormat, LodFilter: true, Binary: true}}


// export all of our files with the default export settings
Logger.Info(`Exporting ${exportSet.size} files...`);
wkit.ExportFiles([...exportSet], exportsettings);
Logger.Success("======================================\nSector export finished!\n\n")

//#region helper_functions
function* GetPaths(jsonData) {
    for (let [key, value] of Object.entries(jsonData || {})) {
        if (value instanceof TypeHelper.ResourcePath && !value.isEmpty()) {
            yield value.value;
        }
        if (typeof value === "object") {
            yield* GetPaths(value);
        }
    }
}

function export_filename(filename){
	// Define a mapping of extensions and their replacements
    const extensionMap = {
        'mesh': 'glb',
        'xbm': imgFormat,
        'w2mesh':'glb',
        'physicalscene':'glb',
	'streamingsector':'streamingsector.json'
        
        // Add more extensions and replacements as needed
    };

    // Find the position of the last occurrence of '.' to get the extension
    const dotIndex = filename.lastIndexOf('.');
    if (dotIndex === -1) {
        // If no extension found, return the filename as it is
        return filename;
    } else {
        // Extract the existing extension
        const extension = filename.substring(dotIndex + 1);

        // Check if the extension exists in the mapping
        if (extensionMap.hasOwnProperty(extension)) {
            // Replace the existing extension with the mapped one
            return filename.substring(0, dotIndex) + '.' + extensionMap[extension];
        } else {
            // If extension not found in mapping, return the filename as it is
            return filename;
        }
    }

}


function convertEmbedded(embeddedFile) {
    let data = TypeHelper.JsonParse(fileTemplate);
    data["Data"]["RootChunk"] = embeddedFile["Content"];
    let jsonString = TypeHelper.JsonStringify(data);

    let cr2w = wkit.JsonToCR2W(jsonString);
    wkit.SaveToProject(embeddedFile["FileName"].value, cr2w);
}

// Parse a CR2W file
function ParseFile(fileName, parentFile) {
    // check if we've already worked with this file and that it's actually a string
    if (parsedFiles.has(fileName)) {
        return;
    }
    parsedFiles.add(fileName);

    let extension = typeof (fileName) !== 'string' ? 'unknown' : `.${fileName.split('.').pop()}`;

    if (extension !== 'unknown') {
        if (!(jsonExtensions.includes(extension) || exportExtensions.includes(extension))) {
            return;
        }
        const embeddedFiles = parentFile?.Data?.EmbeddedFiles || [];
        for (let embeddedFile of embeddedFiles) {
            if (embeddedFile["FileName"].value === fileName) {
            	let embextension = typeof (fileName) !== 'string' ? 'unknown' : `.${fileName.split('.').pop()}`;
            	if (!only_new || (only_new && !wkit.FileExistsInRaw(export_filename(fileName)))){
                	convertEmbedded(embeddedFile);

                	// add nested file to export list
                	    
	                if (jsonExtensions.includes(extension)) jsonSet.add(fileName);
	                if (exportEmbeddedExtensions.includes(embextension)) exportSet.add(fileName);
				}
                return;
            }
        }
    }

    let isHash = false;
    if (typeof (fileName) === 'bigint') {
        isHash = true;
        fileName = fileName.toString();
    }

    if (typeof (fileName) !== 'string') {
        Logger.Error('Unknown path type');
        return;
    }

    let file = null;

    // Load from project if it exists, otherwise get the base game file
    if (wkit.FileExistsInProject(fileName)) {
        file = wkit.GetFileFromProject(fileName, OpenAs.GameFile);
    } else {
        file = wkit.GetFileFromBase(fileName);
    }

    // Let the user know if we failed to export the file
    if (file === null && !suppressLogFileOutput) {
        if (!isHash) {
            Logger.Warning(`Skipping invalid export ${fileName}`);
        } else {
            Logger.Info(`Failed to retrieve file from hash: ${fileName}`);
        }
        return;
    }

    if (!(jsonExtensions.includes(file.Extension) || exportExtensions.includes(file.Extension))) {
        return;
    }
    
    if (!only_new || (only_new && !wkit.FileExistsInRaw(export_filename(fileName)))) projectSet.add(fileName);
    
    
    if (!only_new || (only_new && !wkit.FileExistsInRaw(fileName+'.json'))){
	    if (jsonExtensions.includes(file.Extension)) jsonSet.add(fileName);
	    }
	if (!only_new || (only_new && !wkit.FileExistsInRaw(export_filename(fileName)))){
	    if (exportExtensions.includes(file.Extension)) exportSet.add(fileName);
    	}
    

    // now check if there are referenced files and parse them
    if (file.Extension !== ".xbm") {
        let json = TypeHelper.JsonParse(wkit.GameFileToJson(file));
        for (let path of GetPaths(json["Data"]["RootChunk"])) {
            ParseFile(path, json);
        }
        if (file.Extension == ".streamingsector" && mesh_colliders) {
        Collision_Shapes.Export_Sector_Collisions(json);
        }
    }
}

//#endregion
