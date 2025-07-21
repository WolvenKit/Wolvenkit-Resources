import * as Logger from '../../Logger.wscript';
import * as TypeHelper from '../../TypeHelper.wscript';

/**
 * Returns a map of translation keys
 * @param {string} filePath - Path to the configuration file
 * @returns {Object.<string, <string, string>>} Map `filePath` => `{secondaryKey: {primaryKey: number, secondaryKey: string, femaleVarient: string, maleVariant: string}}`
 */
export function Get_Translation_Entries(filePath)
{
    const ret = {};
    // Parse referenced file and return factory info
    try {
        const file = wkit.GameFileToJson(wkit.GetFileFromProject(filePath, OpenAs.GameFile));
        let json = TypeHelper.JsonParse(file);
        let entries = json.Data.RootChunk.root.Data.entries;
        entries.forEach(entry => {
            ret[entry.secondaryKey] = {
                primaryKey: entry.primaryKey,
                secondaryKey: entry.secondaryKey,
                femaleVariant: entry.femaleVariant,
                maleVariant: entry.maleVariant
            };
        });
    } catch (e) {
        Logger.Error(`Error while parsing ${filePath}: ${e.message}`);
    }
    return ret;
}