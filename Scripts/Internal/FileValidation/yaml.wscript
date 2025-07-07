import * as Logger from '../../Logger.wscript';
import * as Csv from './csv.wscript';
import * as Ent from './ent.wscript';
import * as StringHelper from "../StringHelper.wscript";

// read root entity info only once per run
let rootEntityCache = {};

// read factory info only once per run
let factoryInfoCache = {};

// all root entity info, read once
let entFileInfo = [];

// all factory info, read once
let factoryInfo = [];

// all tweak records, read from wkit
let validRecords = [];

// Collect $base errors
let invalidBases = {};

// Collect entityName errors  
let invalidEntityNames = {};

let itemDefinitionNames = [];

function collectFilePaths(data, filePaths = []) {
    if (!data) {
        return filePaths;
    }
    let keys = Object.keys(data);
    if (keys.length === 0) {
        return filePaths;
    }
    for (let key of keys) {
        let value = data[key];
        if (typeof value === 'string' && ((value.includes('/')|| value.includes('\\') ) && value.includes('.'))) {
            filePaths.push(value);
        } else if (typeof value === 'object') {
            collectFilePaths(value, filePaths);
        }
    }
    return [... new Set(filePaths)]; // remove duplicates
}

function verifyYamlFilePaths(data) {
    const filePaths = collectFilePaths(data);
    const projectFiles = Array.from(wkit.GetProjectFiles('archive'));

    let filesNotFound = filePaths.filter(p => !projectFiles.find(str => str === p));
    
    // if link destination files aren't found, that's fine
    if (data.resource && data.resource.link) {
        const linkKeys = Object.keys(data.resource.link);
        const linkValues = collectFilePaths(data.resource.link).filter(p => !linkKeys.includes(p));
        filesNotFound = filesNotFound.filter(p => !linkValues.includes(p));        
    }

    if (filesNotFound.length > 0) {
        Logger.Error(`The following files were not found in the project:\n\t${filesNotFound.join('\n\t')}`);
    }
}

function getRootEntityInfo() {
    let ret = {};
    const projectFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.ent'));
    projectFiles.forEach((filePath) => {
        if (rootEntityCache[filePath]) {
            return rootEntityCache[filePath];
        }
        rootEntityCache[filePath] = Ent.Get_Entity_Appearances(filePath);

        ret = {...ret, ...rootEntityCache[filePath]};
    });
    return ret;
}

function getFactoryInfo() {
    let ret = {};
    const projectFiles = Array.from(wkit.GetProjectFiles('archive')).filter(f => f.endsWith('.csv'));
    if (projectFiles.length === 0) {
        return ret;
    }
    projectFiles.forEach((filePath) => {
        if (factoryInfoCache[filePath]) {
            return factoryInfoCache[filePath];
        }
        factoryInfoCache[filePath] = Csv.Get_Factory_Info(filePath);
        
        ret = {...ret, ...factoryInfoCache[filePath]};        
    });
    return ret;
}

function getValidRecords() {
    if (!validRecords.length) {
        Array.from(wkit.GetRecords()).forEach(val => validRecords.push(val));        
    }
    return validRecords;
}


function verifyItemDefinition(recordData, recordName) {
    // currently only implemented for clothing items
    if (!recordData?.entityName) {
        Logger.Success(JSON.stringify(recordData, null, 2));
        return;
    }

    const base = recordData["$base"];
    if (!base) {
        invalidBases[recordName] = 'No $base attribute found';
    } else if (!itemDefinitionNames.includes(base) && !getValidRecords().includes(base)) {
        invalidBases[recordName] = `${base}`;
    } else {
        Logger.Success(`base ${base} found for ${recordName}`);
    }
    
    const entityName = recordData.entityName;
    if (!entityName && !itemDefinitionNames.includes(recordName)) {
        invalidEntityNames[recordName] = `Record has no entityName - it will not spawn`;
    }
    if (!Object.keys(entFileInfo).includes(entityName)) {
        invalidEntityNames[recordName] = `${entityName} not registered`;
    }
}

function verifyTweakXlFile(data) {
    factoryInfo = getFactoryInfo();
    entFileInfo = getRootEntityInfo();
    
    Object.keys(data).forEach(key => itemDefinitionNames.push(key));
    
    itemDefinitionNames.forEach((name) => {
        Logger.Success(`Validating item definition: ${name}`);
        verifyItemDefinition(data[name], name);
    });

    if (Object.keys(invalidBases).length > 0) {
        Logger.Warning("File validation found invalid item $base keys. Find a list for clothing in the EquipmentEx wiki:");
        Logger.Info("\thttps://github.com/psiberx/cp2077-equipment-ex?tab=readme-ov-file#auto-conversions");
        Logger.Info("\tIf this is not a clothing item, please check for typos.\n\t"
            + StringHelper.stringifyMap(invalidBases).replaceAll("\n", "\n\t")
        );
    }

    if (Object.keys(invalidEntityNames).length > 0) {
        Logger.Warning("File validation found invalid entity names. Make sure to register them in your .csv file.");
        Logger.Info(`\tValid entity names in your project are: [ ${Object.keys(factoryInfo).join(', ')} ]\n\t`
            + StringHelper.stringifyMap(invalidEntityNames).replaceAll("\n", "\n\t")
        );
    }
}

function reset_caches() {
    factoryInfoCache = {};
    rootEntityCache = {};
    invalidBases = {};
    invalidEntityNames = {};

    factoryInfo = {};
    entFileInfo = {};

    itemDefinitionNames.length = 0;
}

export function validate_yaml_file(data, yaml_settings, isXlFile = false) {
    if (!data) {
        Logger.Info("No data found in YAML file. Skipping validation.")
        return;
    }
    
    reset_caches();
    if (isXlFile) {
        verifyYamlFilePaths(data);        
    } else {
        verifyTweakXlFile(data);
    }
}