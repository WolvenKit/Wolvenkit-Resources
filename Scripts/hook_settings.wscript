// @version 1.0
// @type hook
// @hook_type none
// @hook_extension settings
// ^^^ Just so it's in the hooks tab

/* 
 * See the documentation for more info:
 * https://wiki.redmodding.org/wolvenkit/wolvenkit-app/file-validation
 */
const Settings = {
    Enabled: true,
    /*
     * Under certain circumstances, file validation can correct mistakes in the files.
     * Set this to "true" to disable the feature for good.
     */
    DisableAutofix: false,
    /* .anims files */
    Anims: {
        /*
         * Set this to "false" to disable file validation for .anims files.
         */
        Enabled: true,
        /*
         * Set this to "true" to have the script print all animation names to console
         */
        printAnimationNames: false,

        /*
         * Set this to "false" to disable check for duplicate anims
         */
        checkForDuplicates: true,
    },
    App: {
        /*
         * Set this to "false" to disable file validation for .app files.
         */
        Enabled: true,
        /*
         * Set this to "false" to disable recursive verification in app files
         * (e.g. to check the appearance names against meshes)
         */
        validateRecursively: true,
        /*
         * Set this to "false" to disable warnings about duplicate component names,
         * e.g. "] The following components are defined more than once: [ pants_black ]"
         */
        checkComponentNameDuplication: true,
        /*
         * Set this to "false" to disable warnings about inplaceResources potentially crashing your game.
         */
        checkForCrashyDependencies: true,
        /*
         * Set this to "false" to disable warnings about resolvedDependencies. TODO: Can this go?
         */
        checkForResolvedDependencies: true,
        /*
         * Set this to "false" to disable warnings about components with the same name but different meshes.
         * e.g. if you're loading different variants from the same app file depending on a tag.
         */
        checkPotentialOverrideCollisions: false,
    },
    Csv: {
        /*
         * Set this to "false" to disable file validation for .csv files.
         */
        Enabled: true, 
        /*
         * Set this to "false" to disable the attempted resolution of resource paths
         * e.g. "component: unknown resource in depot path"
         */
        checkProjectResourcePaths: true,
        /*
         * Set this to "false" to disable warnings if a value looks like it's not a depot path, e.g.
         * "One or more entries couldn't be resolved to depot paths. Is this a valid factory?"
         */
        warnAboutInvalidDepotPaths: true
    },
    Ent: {
        /*
         * Set this to "false" to disable file validation for .ent files.
         */
        Enabled: true,
        
        /*
         * Set this to "false" to disable recursive verification of linked .app files
         */
        validateAppsRecursively: true,

        /*
         * Set this to "false" to disable recursive verification of meshes found in linked .app files.
         * This will have no effect if validateAppsRecursively is set to "false"
         */
        validateMeshesRecursively: false,

        /*
         * Set this to "false" to disable warnings about duplicate component names,
         * e.g. "The following components are defined more than once: [ pants_black ]"
         */
        checkComponentNameDuplication: false,

        /*
         * Set this to "false" to disable warnings about component IDs and duplication,
         * e.g. " The following components are defined more than once: [ pants_black ]"
         */
        checkComponentIdsForGarmentSupport: true,

        /*
         * Checks for ArchiveXL >= 1.5's dynamic appearance activator by checking for empty appearance names
         * in the root entity, or the presence of string substitution in nested files.
         */
        checkDynamicAppearanceTag: true,

        /*
         * Checks for {body_type} in dynamic variants and yells at you if you forgot to do refits.
         */
        warnAboutMissingRefits: false,

        /*
         * Set to "false" to suppress warnings about incomplete substitution
         */
        warnAboutIncompleteSubstitution: false,
    },
    Inkatlas: {
        /*
         * Set this to "false" to disable file validation for .inkatlas files.
         */
        Enabled: true,
        /*
         * Set this to "false" to skip path check for dynamicTexture and dynamicTextureSlot
         */
        CheckDynamicTexture: true,
        /*
         * Set this to "false" to skip path check for texture slots (only the first must be set)
         */
        CheckSlots: true,
    },
    Json: {
        /*
         * Set this to "false" to disable file validation for .json files.
         */
        Enabled: true,
        /*
         * Check for primary key duplication and duplicate entries? 
         */
        checkDuplicateKeys: true,
        /*
         * Check for duplicate translation entries (same text) 
         */
        checkDuplicateTranslations: true,        
        /*
         * Warn if default value isn't set? 
         */
        checkEmptyFemaleVariant: true,
    },
    Mesh: {
        /*
         * Set this to "false" to disable file validation for .mesh files.
         */
        Enabled: true,
        /*
         * Should file validation check materials along the daisy chain? (Only outside of /base) 
         */
        validateMaterialsRecursively: true,
        /*
         * If you're using placeholder materials, should file validation warn you about properties in values[]? 
         */
        validatePlaceholderValues: false,
        /*
         * If you're using placeholder materials, should file validation check depot paths? 
         * Incorrect depot paths will cause crashes, so you might want to leave this enabled.
         */
        validatePlaceholderMaterialPaths: true,
        /*
         * Should file validation warn you if two of your materials use the same mlsetup?
         */
        checkDuplicateMlSetupFilePaths: true,
        /*
         * Should file validation warn you if you define a material (by name) twice?
         */
        checkDuplicateMaterialDefinitions: false,
        /*
         * Should file validation verify paths to external materials in your mesh?
         */
        checkExternalMaterialPaths: true,
        /*
         * Should file validation check for appearances without submeshes?
         */
        checkEmptyAppearances: false,
    },
    Mi: {
        /*
         * Set this to "false" to disable file validation for .mi files.
         */
        Enabled: true,
        /*
         * Should file validation check materials along the daisy chain? (Only outside of /base) 
         */
        validateRecursively: true,
    },
    Morphtarget: {
        /*
         * Set this to "false" to disable file validation for .mi files.
         */
        Enabled: true,
        /*
         * Should file validation check materials in inherited meshes? (Only outside of /base) 
         */
        validateRecursively: true,
    },    
    InkCC: {
        /*
         * Set this to "false" to disable file validation for .inkcc files.
         */
        Enabled: true,
    },
    
    Workspot: {
        /*
         * Set this to "false" to disable file validation for .workspot files.
         */
        Enabled: true,
        /*
         * Disable reordering of file indices in the workspot. Will do nothing if:
         * - Settings.DisableAutofix is true
         */
        fixIndexOrder: true,

        /*
         * Disable reordering of file indices in the workspot. Will do nothing if: 
         * - Settings.DisableAutofix is true
         * - Settings.Workspot.fixIndexOrder is false
         */
        autoReopenFile: false,

        /*
         * Set this to "false" to suppress the warning "Items from .anim files not found in .workspot:"
         */
        showUnusedAnimsInFiles: true,

        /*
         * Set this to "false" to suppress the warning "Items from .workspot not found in .anim files:"
         */
        showUndefinedWorkspotAnims: true,

        /*
         * Set this to "false" to suppress the info about "idle animation name "xxxx" not found in […]""
         */
        checkIdleAnimNames: true,

        /*
         * Display info about "id already used by…". This will do nothing if you have fixIndexOrder enabled!
         */
        checkIdDuplication: true,

        /*
         * Set this to "false" to suppress checking of nested files in workspot.
         */
        checkFilepaths: true,
    },
    GraphQuestphase: {
        /*
         * Set this to "false" to disable file validation for .questphase files.
         */
        Enabled: true,
    },
    GraphScene: {
        /*
         * Set this to "false" to disable file validation for .scene files.
         */
        Enabled: true,
    }
};

export default Settings;
