// For archive XL dynamic substitution: It will be easier to maintain this in an external file, rather than
// touching FileValidation each time something changes.
export class ArchiveXLConstants {
    // When adding a body here, make sure to add it to the right genderToBodyMap as well!
    static allPotentialBodies = [
        'base_body', 
        'lush', 
        'adonis'
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
}