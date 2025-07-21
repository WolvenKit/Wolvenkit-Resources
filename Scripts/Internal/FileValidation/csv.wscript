import * as Logger from '../../Logger.wscript';
import * as TypeHelper from '../../TypeHelper.wscript';

/**
 * Returns a map of factory info from the file (which entity names use which root entity)
 * @param {string} filePath - Path to the configuration file
 * @returns {Object.<string, string>} Map `entityName` => `rootEntityPath`
 */
export function Get_Factory_Info(filePath)
{
    const ret = {};
    // Parse referenced file and return factory info
    try {
        const file = wkit.GameFileToJson(wkit.GetFileFromProject(filePath, OpenAs.GameFile));
        let json = TypeHelper.JsonParse(file);

        (json?.Data?.RootChunk?.compiledData ?? {}).forEach((item) => {
            if (item.Length < 2)
            {
                return;
            }
            ret[item[0]] = item[1];
        });
    } catch (e) {
        Logger.Error(`Error while parsing ${filePath}: ${e.message}`);
    }
    return ret;
}