# faction_generator.py
import random
from typing import List, Dict, Tuple
from faction_system.faction_system import Faction, FactionManager, FactionType, RelationshipStatus

class FactionGenerator:
    """Handles procedural generation of factions based on world state"""
    
    # Name components for different faction types
    FACTION_NAME_PARTS = {
        FactionType.GOVERNMENT: {
            "prefixes": ["Imperial", "Royal", "Republic of", "United", "Federated", "Democratic", "Sovereign"],
            "roots": ["Council", "Senate", "Parliament", "Court", "Assembly", "Monarchy", "Dominion"],
            "suffixes": ["Authority", "Order", "Regency", "Coalition", "Alliance", "Union"]
        },
        FactionType.CRIMINAL: {
            "prefixes": ["Shadow", "Black", "Iron", "Blood", "Night", "Crimson", "Phantom"],
            "roots": ["Hand", "Dagger", "Serpent", "Wolf", "Raven", "Cobra", "Viper"],
            "suffixes": ["Gang", "Syndicate", "Cartel", "Brotherhood", "Family", "Network", "Ring"]
        },
        FactionType.MERCHANT: {
            "prefixes": ["Golden", "Silver", "Trade", "Commerce", "Merchant", "Free", "Royal"],
            "roots": ["Road", "Sea", "Venture", "Market", "Exchange", "Harbor", "Caravan"],
            "suffixes": ["Guild", "Company", "Consortium", "Association", "Enterprise", "Inc.", "Trading Co."]
        },
        FactionType.RELIGIOUS: {
            "prefixes": ["Divine", "Holy", "Sacred", "Blessed", "Radiant", "Eternal", "Celestial"],
            "roots": ["Light", "Temple", "Faith", "Covenant", "Prayer", "Spirit", "Soul"],
            "suffixes": ["Order", "Church", "Brotherhood", "Circle", "Assembly", "Followers", "Disciples"]
        },
        FactionType.MILITARY: {
            "prefixes": ["Iron", "Steel", "Elite", "Veteran", "Royal", "First", "Grand"],
            "roots": ["Sword", "Shield", "Fist", "Spear", "Legion", "Guards", "Warriors"],
            "suffixes": ["Battalion", "Regiment", "Corps", "Brigade", "Army", "Defenders", "Protectors"]
        },
        FactionType.GUILD: {
            "prefixes": ["Master", "Expert", "Skilled", "United", "Ancient", "Noble", "Honored"],
            "roots": ["Craft", "Art", "Skill", "Trade", "Labor", "Talent", "Profession"],
            "suffixes": ["Guild", "Society", "Union", "Association", "Fellowship", "Collective", "League"]
        },
        FactionType.TRIBAL: {
            "prefixes": ["Great", "Wild", "Ancient", "Primal", "Native", "Sacred", "Eternal"],
            "roots": ["Bear", "Wolf", "Eagle", "Tiger", "Hawk", "Lion", "Snake"],
            "suffixes": ["Tribe", "Clan", "People", "Nation", "Folk", "Kin", "Children"]
        }
    }
    
    # Faction color palettes by type
    FACTION_COLORS = {
        FactionType.GOVERNMENT: [
            ((25, 55, 125), (200, 200, 255)),  # Blue and light blue
            ((70, 30, 90), (180, 140, 200)),   # Purple and lavender
            ((120, 65, 15), (210, 175, 120)),  # Brown and tan
        ],
        FactionType.CRIMINAL: [
            ((20, 20, 20), (100, 100, 100)),   # Black and gray
            ((100, 0, 0), (200, 50, 50)),      # Dark red and red
            ((25, 25, 40), (60, 60, 80)),      # Dark blue-gray
        ],
        FactionType.MERCHANT: [
            ((190, 150, 10), (255, 215, 0)),   # Gold and yellow
            ((90, 140, 40), (150, 200, 80)),   # Green
            ((100, 80, 60), (180, 150, 120)),  # Brown
        ],
        FactionType.RELIGIOUS: [
            ((255, 215, 0), (255, 255, 220)),  # Gold and cream
            ((255, 255, 255), (200, 230, 255)), # White and light blue
            ((100, 30, 120), (200, 150, 220)), # Purple
        ],
        FactionType.MILITARY: [
            ((30, 50, 30), (100, 120, 100)),   # Dark green
            ((90, 10, 10), (150, 40, 40)),     # Dark red
            ((40, 40, 60), (80, 80, 120)),     # Navy blue
        ],
        FactionType.GUILD: [
            ((70, 40, 20), (150, 100, 50)),    # Brown
            ((40, 80, 100), (100, 150, 180)),  # Blue-gray
            ((80, 30, 30), (140, 80, 80)),     # Burgundy
        ],
        FactionType.TRIBAL: [
            ((140, 70, 20), (200, 120, 40)),   # Orange-brown
            ((60, 100, 40), (120, 160, 80)),   # Forest green
            ((100, 40, 40), (180, 90, 80)),    # Reddish brown
        ]
    }

    @classmethod
    def generate_faction_name(cls, faction_type: FactionType) -> str:
        """Generate a random name for a faction based on its type"""
        parts = cls.FACTION_NAME_PARTS[faction_type]
        
        # Decide on name structure
        structure = random.choice([
            "{prefix} {root}",
            "{root} of {suffix}",
            "The {prefix} {root}",
            "{prefix} {root} {suffix}",
            "The {root} {suffix}",
            "{root} {suffix}"
        ])
        
        # Fill in the structure with random parts
        name_parts = {
            "prefix": random.choice(parts["prefixes"]),
            "root": random.choice(parts["roots"]),
            "suffix": random.choice(parts["suffixes"])
        }
        
        return structure.format(**name_parts)

    @classmethod
    def generate_faction_colors(cls, faction_type: FactionType) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Generate primary and secondary colors for a faction based on its type"""
        return random.choice(cls.FACTION_COLORS[faction_type])

    @classmethod
    def generate_faction_description(cls, faction_type: FactionType, name: str) -> str:
        """Generate a description for a faction based on its type and name"""
        descriptions = {
            FactionType.GOVERNMENT: [
                f"The ruling authority of the region, {name} maintains order through law and bureaucracy.",
                f"A governing body that controls much of the civilized lands, {name} enforces its laws with an iron fist.",
                f"The official governing power, {name} collects taxes and maintains infrastructure across its territories."
            ],
            FactionType.CRIMINAL: [
                f"Operating in the shadows of society, {name} controls much of the region's illicit activities.",
                f"A notorious criminal organization, {name} thrives on smuggling, theft, and extortion.",
                f"Few speak of {name} openly, but their influence in the criminal underworld is undeniable."
            ],
            FactionType.MERCHANT: [
                f"Controlling vital trade routes, {name} has amassed considerable wealth and influence.",
                f"With a network of traders and markets, {name} facilitates commerce throughout the region.",
                f"Through shrewd business practices, {name} has become a dominant economic force."
            ],
            FactionType.RELIGIOUS: [
                f"Devoted to spreading their faith, {name} seeks to guide the spiritual lives of all people.",
                f"The faithful of {name} can be found throughout the land, praying for divine guidance.",
                f"Ancient traditions and rituals are preserved by the devout followers of {name}."
            ],
            FactionType.MILITARY: [
                f"Hardened warriors make up the ranks of {name}, ready to defend their territory at all costs.",
                f"Through rigorous training and discipline, {name} maintains its reputation as a formidable fighting force.",
                f"The soldiers of {name} are known for their bravery and loyalty on the battlefield."
            ],
            FactionType.GUILD: [
                f"Skilled artisans and craftspeople comprise {name}, preserving ancient techniques and knowledge.",
                f"Membership in {name} is highly sought after, as it guarantees quality and fair prices.",
                f"The masters of {name} guard their trade secrets carefully while training the next generation."
            ],
            FactionType.TRIBAL: [
                f"Living in harmony with nature, {name} preserves ancient traditions and wisdom.",
                f"The people of {name} are bound by blood and tradition, following ways unchanged for generations.",
                f"Though often misunderstood by outsiders, {name} maintains a rich cultural heritage."
            ]
        }
        
        return random.choice(descriptions[faction_type])

    @classmethod
    def generate_default_factions(cls) -> FactionManager:
        """Generate a set of default factions for a new game"""
        manager = FactionManager()
        
        # Create one faction of each type
        for faction_type in FactionType:
            # Generate basic faction attributes
            name = cls.generate_faction_name(faction_type)
            description = cls.generate_faction_description(faction_type, name)
            primary_color, secondary_color = cls.generate_faction_colors(faction_type)
            
            # Create ID from name
            faction_id = name.lower().replace(" ", "_").replace("'", "").replace(".", "")
            
            # Create faction with special attributes based on type
            faction = Faction(
                id=faction_id,
                name=name,
                faction_type=faction_type,
                description=description,
                primary_color=primary_color,
                secondary_color=secondary_color,
                # Special attributes
                can_arrest=(faction_type in [FactionType.GOVERNMENT, FactionType.MILITARY]),
                has_slavery=(faction_type in [FactionType.CRIMINAL, FactionType.TRIBAL] and random.random() < 0.5),
                is_hidden=(faction_type == FactionType.CRIMINAL and random.random() < 0.7),
                power_level=random.randint(30, 70)
            )
            
            manager.add_faction(faction)
        
        # Set relationships between factions
        cls._setup_default_relationships(manager)
        
        return manager
    
    @classmethod
    def _setup_default_relationships(cls, manager: FactionManager) -> None:
        """Setup default relationships between generated factions"""
        # Get factions by type for easier reference
        government_factions = manager.get_factions_by_type(FactionType.GOVERNMENT)
        criminal_factions = manager.get_factions_by_type(FactionType.CRIMINAL)
        merchant_factions = manager.get_factions_by_type(FactionType.MERCHANT)
        religious_factions = manager.get_factions_by_type(FactionType.RELIGIOUS)
        military_factions = manager.get_factions_by_type(FactionType.MILITARY)
        guild_factions = manager.get_factions_by_type(FactionType.GUILD)
        tribal_factions = manager.get_factions_by_type(FactionType.TRIBAL)
        
        # Default relationships (can be expanded)
        
        # Government versus others
        for gov in government_factions:
            for crim in criminal_factions:
                manager.set_relationship(gov.id, crim.id, RelationshipStatus.HOSTILE)
            
            for mil in military_factions:
                manager.set_relationship(gov.id, mil.id, RelationshipStatus.ALLIED)
            
            for merch in merchant_factions:
                manager.set_relationship(gov.id, merch.id, RelationshipStatus.FRIENDLY)
            
            for guild in guild_factions:
                manager.set_relationship(gov.id, guild.id, RelationshipStatus.FRIENDLY)
            
            for tribe in tribal_factions:
                # Governments often have complex relationships with tribes
                manager.set_relationship(gov.id, tribe.id, random.choice([
                    RelationshipStatus.UNFRIENDLY, 
                    RelationshipStatus.NEUTRAL,
                    RelationshipStatus.FRIENDLY
                ]))
            
            for rel in religious_factions:
                # Can be allied or neutral depending on theocracy levels
                manager.set_relationship(gov.id, rel.id, random.choice([
                    RelationshipStatus.NEUTRAL,
                    RelationshipStatus.FRIENDLY,
                    RelationshipStatus.ALLIED
                ]))
        
        # Criminal versus others
        for crim in criminal_factions:
            for mil in military_factions:
                manager.set_relationship(crim.id, mil.id, RelationshipStatus.HOSTILE)
            
            for merch in merchant_factions:
                # Sometimes have arrangements, sometimes are at odds
                manager.set_relationship(crim.id, merch.id, random.choice([
                    RelationshipStatus.UNFRIENDLY,
                    RelationshipStatus.NEUTRAL
                ]))
            
            for rel in religious_factions:
                manager.set_relationship(crim.id, rel.id, RelationshipStatus.UNFRIENDLY)
        
        # Add some random variation to the default patterns
        all_factions = list(manager.factions.values())
        num_random_relationships = len(all_factions) // 2
        
        for _ in range(num_random_relationships):
            f1 = random.choice(all_factions)
            f2 = random.choice(all_factions)
            
            if f1.id != f2.id:
                status = random.choice(list(RelationshipStatus))
                manager.set_relationship(f1.id, f2.id, status)


# Example usage
if __name__ == "__main__":
    # Generate default factions
    faction_manager = FactionGenerator.generate_default_factions()
    
    # Print out the generated factions
    for faction_id, faction in faction_manager.factions.items():
        print(f"Created faction: {faction.name} ({faction.faction_type.name})")
        print(f"  Description: {faction.description}")
        print(f"  Colors: Primary={faction.primary_color}, Secondary={faction.secondary_color}")
        print(f"  Special attributes: Can arrest={faction.can_arrest}, Has slavery={faction.has_slavery}")
        print()
    
    # Print some relationships
    for f1 in list(faction_manager.factions.keys())[:3]:
        for f2 in list(faction_manager.factions.keys())[3:]:
            rel = faction_manager.get_relationship(f1, f2)
            print(f"Relationship between {faction_manager.factions[f1].name} and {faction_manager.factions[f2].name}: {rel.name}")
    
    # Save to file
    faction_manager.save_to_file("default_factions.json")
    print("\nFaction data saved to default_factions.json")
