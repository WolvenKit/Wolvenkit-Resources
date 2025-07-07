import * as Logger from '../../Logger.wscript';
import * as TypeHelper from '../../TypeHelper.wscript';

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