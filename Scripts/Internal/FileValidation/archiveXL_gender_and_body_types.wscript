// @type lib
// @name FileValidation_BodyTypes

// For archive XL dynamic substitution: It will be easier to maintain this in an external file, rather than
// touching FileValidation each time something changes.
export class ArchiveXLConstants {
    // When adding a body here, make sure to add it to the right genderToBodyMap as well!
    static allPotentialBodies = [
        'base_body', 
        'lush', 
        // 'adonis'
    ];
    
    // Which bodies from the array above are valid for which body gender?
    static genderToBodyMap = {
        'm': [
            'base_body',
            // 'adonis',
        ],
        'w': [
            'base_body', 
            'lush',
        ],
    }
    
    static validClothingBaseTypes = [
        // Base items
        "Items.GenericHeadClothing",
        "Items.Glasses",
        "Items.Visor",
        "Items.GenericFaceClothing",
        "Items.GenericInnerChestClothing",
        "Items.GenericOuterChestClothing",
        "Items.GenericLegClothing",
        "Items.Skirt",
        "Items.GenericFootClothing",
        "Items.Outfit",

        // Head items
        "Items.HelmetHair",
        "Items.Hat",
        "Items.Cap",
        "Items.Scarf",
        "Items.ScarfHair",
        "Items.Balaclava",
        
        // Face item
        "Items.Glasses",
        "Items.Mask",
        "Items.Visor",
        "Items.Tech",
        
        // T2
        "Items.Coat",
        "Items.Dress",
        "Items.FormalJacket",
        "Items.Jacket",
        "Items.Jumpsuit",
        "Items.LooseShirt",
        "Items.Vest",
        
        // T1
        "Items.FormalShirt",
        "Items.Shirt",
        "Items.TankTop",
        "Items.TightJumpsuit",
        "Items.TShirt",
        "Items.Undershirt",

        // Legs
        "Items.FormalPants",
        "Items.Pants",
        "Items.Shorts",
        "Items.Skirt",
        
        // Feet
        "Items.Boots",
        "Items.CasualShoes",
        "Items.FormalShoe",
    ];
}