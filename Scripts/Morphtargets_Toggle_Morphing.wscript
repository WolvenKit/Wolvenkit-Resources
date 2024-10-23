import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';

const enableMorphing = false;


const files = [];

for (let filename of wkit.GetProjectFiles('archive')) {
    // Logger.Success(filename);
    if (filename.split('.').pop() === "morphtarget") {
        files.push(filename);
    }
}

// loop over every sector in `sectors`
for (let file in files) {
    Logger.Info(`Parsing morphtarget...${files[file]}`);
    ParseFile(files[file], null);
}

function ParseFile(filePath) {
    if (!wkit.FileExistsInProject(filePath)) {
        return;
    }    
    const file = wkit.GetFileFromProject(filePath, OpenAs.GameFile);
    const json = TypeHelper.JsonParse(wkit.GameFileToJson(file));
    const header = json["Data"]["RootChunk"]["blob"]["Data"]["header"];
    header["numTargets"] = enableMorphing ? header["numVertexDiffsInEachChunk"].length : 0;
   
    let jsonString = '';
    try {
        jsonString = TypeHelper.JsonStringify(json);
    } catch (err) {
        Logger.Error(`Couldn't parse active file content to json:`);
        Logger.Error(err);
        return;
    }
    
    let cr2wContent;
    try {
        cr2wContent = wkit.JsonToCR2W(jsonString)
    } catch (err) {
        Logger.Error(`Couldn't parse active file content to cr2w:`);
        Logger.Error(err);
        return;
    }

    try {
        wkit.SaveToProject(filePath, cr2wContent);
    } catch (err) {
        Logger.Error(`Couldn't save ${activeFilePath}:`);
        Logger.Error(err);
    }
}