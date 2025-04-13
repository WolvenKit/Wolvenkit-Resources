interface GameFile {
    Extension: string,
    Name: string,
}

/**
 * WolvenKit API - exposed via ScriptFunctions.cs and AppScriptFunctions.cs
 */
declare namespace wkit {
    enum OpenAs {
        GameFile = "GameFile",
        CR2W = "CR2W",
        Json = "Json"
    }


    enum WMessageBoxImage {
        // Add actual enum values if available
    }

    enum WMessageBoxButtons {
        // Add actual enum values if available
    }

    enum WMessageBoxResult {
        // Add actual enum values if available
    }

    interface ScriptDocumentWrapper {
        // Define properties/methods as needed
    }

    /**
     * Turn on/off updates to the project tree
     * @param suspend bool for if updates are suspended
     * @deprecated
     */
    function SuspendFileWatcher(suspend: boolean): void;

    /**
     * Add the specified file to the project
     * @param path The file to write to
     * @param file CR2WFile or IGameFile to be saved
     */
    function SaveToProject(path: string, file: any): void;

    /**
     * Save the specified text to the specified path in the raw folder
     * @param path The file to write to
     * @param content The string to write to the file
     */
    function SaveToRaw(path: string, content: string): void;

    /**
     * Save the specified text to the specified path in the resources folder
     * @param path The file to write to
     * @param content The string to write to the file
     */
    function SaveToResources(path: string, content: string): void;

    /**
     * Loads the content of a text file from resources
     * @param path The relative path of the text file
     * @returns The content or null
     */
    function LoadFromResources(path: string): string | null | undefined;

    /**
     * Loads the specified game file from the project files
     * @param path The file to open for reading
     * @param type The type of the object which is returned. Can be "cr2w" or "json"
     */
    function LoadGameFileFromProject(path: string, type: "cr2w" | "json"): any | null | undefined;

    /**
     * Loads the specified json file from the project raw files
     * @param path The file to open for reading
     * @param type The type of the object which is returned. Can be "cr2w" or "json"
     */
    function LoadRawJsonFromProject(path: string, type: "cr2w" | "json"): any | null | undefined;

    /**
     * Retrieves a list of files from the project
     * @param folderType string parameter folderType = "archive" or "raw"
     */
    function GetProjectFiles(folderType: "archive" | "raw" | "resources"): string[];

    /**
     * Clears the lookup for exported depot files
     */
    function ClearExportFileLookup(): void;

    /**
     * Exports a list of files as you would with the export tool
     * @param fileList
     * @param defaultSettings
     */
    function ExportFiles(fileList: any[], defaultSettings?: any): void;

    /**
     * Loads a file from the project using either a file path or hash
     * @param path The path of the file to retrieve
     * @param openAs The output format (OpenAs.GameFile, OpenAs.CR2W or OpenAs.Json)
     * @returns { GameFile | null | undefined } file
     */
    function GetFileFromProject(path: string, openAs: OpenAs): GameFile | null | undefined;

    /**
     * Loads a file from the project using either a file path or hash
     * @param hash The hash of the file to retrieve
     * @param openAs The output format (OpenAs.GameFile, OpenAs.CR2W or OpenAs.Json)
     * @returns { GameFile | null | undefined } file
     */
    function GetFileFromProject(hash: number, openAs: OpenAs): GameFile | null | undefined;

    /**
     * Loads a file from the project or archive (in this order) using either a file path or hash
     * @param path The path of the file to retrieve
     * @param openAs The output format (OpenAs.GameFile, OpenAs.CR2W or OpenAs.Json)
     */
    function GetFile(path: string, openAs: OpenAs): GameFile | null | undefined;

    /**
     * Loads a file from the project or archive (in this order) using either a file path or hash
     * @param hash The hash of the file to retrieve
     * @param openAs The output format (OpenAs.GameFile, OpenAs.CR2W or OpenAs.Json)
     */
    function GetFile(hash: number, openAs: OpenAs): GameFile | null | undefined;

    /**
     * Check if file exists in the project
     * @param path file path to check
     */
    function FileExistsInProject(path: string): boolean;

    /**
     * Check if file exists in the project
     * @param hash hash value to be checked
     */
    function FileExistsInProject(hash: number): boolean;

    /**
     * Check if file exists in either the game archives or the project
     * @param path file path to check
     */
    function FileExists(path: string): boolean;

    /**
     * Check if file exists in either the game archives or the project
     * @param hash hash value to be checked
     */
    function FileExists(hash: number): boolean;

    /**
     * Check if file exists in the project Raw folder
     * @param filepath relative filepath to be checked
     */
    function FileExistsInRaw(filepath: string): boolean;

    /**
     * Deletes a file from the project, if it exists
     * @param filepath relative filepath to be deleted
     * @param folderType project subfolder type (archive|raw|resources)
     * @returns true if the file was deleted
     */
    function DeleteFile(filepath: string, folderType: "archive" | "raw" | "resources"): boolean;

    // TweakDB functions
    function GetRecords(): string[];
    function GetFlats(): string[];
    function GetQueries(): string[];
    function GetGroupTags(): string[];
    function GetRecord(path: string): string | null | undefined;
    function GetFlat(path: string): string | null | undefined;
    function GetQuery(path: string): string[];
    function GetGroupTag(path: string): number | null | undefined;
    function HasTDBID(path: string): boolean;
    function GetTDBIDPath(key: number): string | null | undefined;

    /**
     * Displays a message box
     * @param text A string that specifies the text to display
     * @param caption A string that specifies the title bar caption to display
     * @param image A WMessageBoxImage value that specifies the icon to display
     * @param buttons A WMessageBoxButtons value that specifies which buttons to display
     * @returns A WMessageBoxResult value
     */
    function ShowMessageBox(text: string, caption: string, image: WMessageBoxImage, buttons: WMessageBoxButtons): WMessageBoxResult;

    /**
     * Extracts a file from the base archive and adds it to the project
     * @param path Path of the game file
     */
    function Extract(path: string): void;

    /**
     * Gets the current active document from the docking manager
     */
    function GetActiveDocument(): ScriptDocumentWrapper | null | undefined;

    /**
     * Gets all documents from the docking manager
     */
    function GetDocuments(): ScriptDocumentWrapper[] | null | undefined;

    /**
     * Opens a file in WolvenKit
     * @param path Path to the file
     * @returns Returns true if the file was opened, otherwise it returns false
     */
    function OpenDocument(path: string): boolean;

    /**
     * Opens an archive game file
     * @param gameFile The game file to open
     */
    function OpenDocument(gameFile: any): void;

    /**
     * Exports an geometry_cache entry
     * @param sectorHashStr Sector hash as string
     * @param entryHashStr Entry hash as string
     */
    function ExportGeometryCacheEntry(sectorHashStr: string, entryHashStr: string): string | null | undefined;

    /**
     * Creates a new instance of the given class, and returns it converted to a JSON string
     * @param className Name of the class
     */
    function CreateInstanceAsJSON(className: string): any | null | undefined;

    /**
     * Returns the hashcode for a given string
     * @param data String to be hashed
     * @param method Hash method to use. Can be "fnv1a64" or "default"
     */
    function HashString(data: string, method: "fnv1a64" | "default"): number | null | undefined;

    /**
     * Pauses the execution of the script for the specified amount of milliseconds
     * @param milliseconds The number of milliseconds to sleep
     */
    function Sleep(milliseconds: number): void;

    /**
     * Returns the current wolvenkit version
     */
    function ProgramVersion(): string;

    /**
     * Shows the settings dialog for the supplied data
     * @param data A JavaScript object containing data
     * @returns Returns true when the user changed the settings, otherwise it returns false
     */
    function ShowSettings(data: any): boolean;
    
    /**
     * Gets a list of the files available in the game archives
     */
    function GetArchiveFiles(): Iterable<any>;

    /**
     * DEPRECATED: Please use getFileFromArchive(path, OpenAs.GameFile)
     * Loads a file from the base archives using either a file path or hash
     * @param path The path of the file to retrieve
     */
    function GetFileFromBase(path: string): any | null | undefined;

    /**
     * DEPRECATED: Please use getFileFromArchive(hash, OpenAs.GameFile)
     * Loads a file from the base archives using either a file path or hash
     * @param hash The hash of the file to retrieve
     */
    function GetFileFromBase(hash: number): any | null | undefined;

    /**
     * Creates a json representation of the specifed game file.
     * @param gameFile The gameFile which should be converted
     */
    function GameFileToJson(gameFile: any): string | null | undefined;

    /**
     * DEPRECATED: Creates a CR2W game file from a json
     * @param json
     */
    function JsonToCR2W(json: string): any | null | undefined;

    /**
     * Changes the extension of the provided string path
     * @param path The path of the file to change
     * @param extension
     */
    function ChangeExtension(path: string, extension: string): string;

    /**
     * Loads a file from the base archives using either a file path or hash
     * @param path The path of the file to retrieve
     * @param openAs The output format (OpenAs.GameFile, OpenAs.CR2W or OpenAs.Json)
     */
    function GetFileFromArchive(path: string, openAs: OpenAs): any | null | undefined;

    /**
     * Loads a file from the base archives using either a file path or hash
     * @param hash The hash of the file to retrieve
     * @param openAs The output format (OpenAs.GameFile, OpenAs.CR2W or OpenAs.Json)
     */
    function GetFileFromArchive(hash: number, openAs: OpenAs): any | null | undefined;

    /**
     * Check if file exists in the game archives
     * @param path file path to check
     */
    function FileExistsInArchive(path: string): boolean;

    /**
     * Check if file exists in the game archives
     * @param hash hash value to be checked
     */
    function FileExistsInArchive(hash: number): boolean;

    /**
     * Converts a YAML string to a JSON string
     * @param yamlText The YAML string to convert
     * @returns The converted JSON string
     */
    function YamlToJson(yamlText: string): string;

    /**
     * Converts a JSON string to a YAML string
     * @param jsonText The JSON string to convert
     * @returns The converted YAML string
     */
    function JsonToYaml(jsonText: string): string;
}