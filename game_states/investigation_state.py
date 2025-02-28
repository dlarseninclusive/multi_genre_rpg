import pygame
import logging
import random
from enum import Enum
from game_state import GameState

logger = logging.getLogger("investigation")

class EvidenceType(Enum):
    """Types of evidence that can be found during investigations."""
    PHYSICAL = 0   # Physical objects
    TESTIMONY = 1  # Witness statements
    DOCUMENT = 2   # Documents and records
    PHOTO = 3      # Photographs
    FORENSIC = 4   # Scientific evidence

class Suspect:
    """Represents a suspect in a case."""
    
    def __init__(self, name, description, motive=None, alibi=None, guilt_level=0):
        """
        Initialize a suspect.
        
        Args:
            name: Suspect's name
            description: Physical description
            motive: Reason suspect might have committed crime (None if unknown)
            alibi: Suspect's alibi (None if unknown)
            guilt_level: How guilty they are (0-100, 0 = innocent, 100 = guilty)
        """
        self.name = name
        self.description = description
        self.motive = motive
        self.alibi = alibi
        self.guilt_level = guilt_level
        self.interrogated = False
        self.contradictions = []  # List of evidence that contradicts their statements
        self.notes = []  # Player's notes about the suspect
    
    def interrogate(self):
        """Mark suspect as interrogated."""
        self.interrogated = True
    
    def add_contradiction(self, evidence):
        """
        Add evidence that contradicts suspect's statements.
        
        Args:
            evidence: Evidence instance that contradicts this suspect
        """
        if evidence not in self.contradictions:
            self.contradictions.append(evidence)
    
    def add_note(self, note):
        """
        Add a note about the suspect.
        
        Args:
            note: Text note to add
        """
        self.notes.append(note)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'motive': self.motive,
            'alibi': self.alibi,
            'guilt_level': self.guilt_level,
            'interrogated': self.interrogated,
            'contradictions': [evidence.id for evidence in self.contradictions],
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data, evidence_list=None):
        """Create from dictionary."""
        suspect = cls(
            data['name'],
            data['description'],
            data['motive'],
            data['alibi'],
            data['guilt_level']
        )
        suspect.interrogated = data['interrogated']
        suspect.notes = data['notes']
        
        # Restore contradictions if evidence list is provided
        if evidence_list:
            for evidence_id in data['contradictions']:
                evidence = next((e for e in evidence_list if e.id == evidence_id), None)
                if evidence:
                    suspect.contradictions.append(evidence)
        
        return suspect

class Evidence:
    """Represents a piece of evidence in a case."""
    
    def __init__(self, id, name, description, evidence_type, location=None, related_suspects=None):
        """
        Initialize evidence.
        
        Args:
            id: Unique identifier
            name: Evidence name
            description: Description of the evidence
            evidence_type: Type from EvidenceType enum
            location: Where the evidence was found
            related_suspects: List of suspect names related to this evidence
        """
        self.id = id
        self.name = name
        self.description = description
        self.evidence_type = evidence_type
        self.location = location
        self.related_suspects = related_suspects if related_suspects else []
        self.discovered = False
        self.analyzed = False
        self.notes = []  # Player's notes about the evidence
    
    def discover(self):
        """Mark evidence as discovered."""
        self.discovered = True
    
    def analyze(self):
        """Mark evidence as analyzed."""
        self.analyzed = True
    
    def add_note(self, note):
        """
        Add a note about the evidence.
        
        Args:
            note: Text note to add
        """
        self.notes.append(note)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'evidence_type': self.evidence_type.value,
            'location': self.location,
            'related_suspects': self.related_suspects,
            'discovered': self.discovered,
            'analyzed': self.analyzed,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        evidence = cls(
            data['id'],
            data['name'],
            data['description'],
            EvidenceType(data['evidence_type']),
            data['location'],
            data['related_suspects']
        )
        evidence.discovered = data['discovered']
        evidence.analyzed = data['analyzed']
        evidence.notes = data['notes']
        return evidence

class Location:
    """Represents a location in a case that can be searched for evidence."""
    
    def __init__(self, name, description, evidence_ids=None, visited=False):
        """
        Initialize a location.
        
        Args:
            name: Location name
            description: Description of the location
            evidence_ids: List of evidence IDs that can be found here
            visited: Whether the location has been visited
        """
        self.name = name
        self.description = description
        self.evidence_ids = evidence_ids if evidence_ids else []
        self.visited = visited
        self.searched = False
        self.notes = []  # Player's notes about the location
    
    def visit(self):
        """Mark location as visited."""
        self.visited = True
    
    def search(self):
        """Mark location as searched."""
        self.searched = True
    
    def add_note(self, note):
        """
        Add a note about the location.
        
        Args:
            note: Text note to add
        """
        self.notes.append(note)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'evidence_ids': self.evidence_ids,
            'visited': self.visited,
            'searched': self.searched,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        location = cls(
            data['name'],
            data['description'],
            data['evidence_ids'],
            data['visited']
        )
        location.searched = data['searched']
        location.notes = data['notes']
        return location

class Witness:
    """Represents a witness in a case."""
    
    def __init__(self, name, description, testimony=None):
        """
        Initialize a witness.
        
        Args:
            name: Witness name
            description: Description of the witness
            testimony: Witness's statement about the case
        """
        self.name = name
        self.description = description
        self.testimony = testimony
        self.interviewed = False
        self.reliability = random.randint(50, 100)  # How reliable their testimony is (0-100)
        self.notes = []  # Player's notes about the witness
    
    def interview(self):
        """Mark witness as interviewed."""
        self.interviewed = True
    
    def add_note(self, note):
        """
        Add a note about the witness.
        
        Args:
            note: Text note to add
        """
        self.notes.append(note)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'testimony': self.testimony,
            'interviewed': self.interviewed,
            'reliability': self.reliability,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        witness = cls(
            data['name'],
            data['description'],
            data['testimony']
        )
        witness.interviewed = data['interviewed']
        witness.reliability = data['reliability']
        witness.notes = data['notes']
        return witness

class Case:
    """Represents a detective case with evidence, suspects, and witnesses."""
    
    def __init__(self, title, description, crime_type):
        """
        Initialize a case.
        
        Args:
            title: Case title
            description: Brief description of the case
            crime_type: Type of crime (e.g., "murder", "theft")
        """
        self.title = title
        self.description = description
        self.crime_type = crime_type
        self.status = "open"  # open, solved, closed
        self.evidence = []
        self.suspects = []
        self.witnesses = []
        self.locations = []
        self.notes = []
        self.current_theory = ""
        self.solved_suspect = None  # Who player thinks committed the crime
        self.actual_culprit = None  # Actual guilty party
        self.case_file = []  # Documents related to the case
        self.time_spent = 0  # Time spent on the case
    
    def add_evidence(self, evidence):
        """
        Add evidence to the case.
        
        Args:
            evidence: Evidence instance
        """
        self.evidence.append(evidence)
    
    def add_suspect(self, suspect):
        """
        Add suspect to the case.
        
        Args:
            suspect: Suspect instance
        """
        self.suspects.append(suspect)
    
    def add_witness(self, witness):
        """
        Add witness to the case.
        
        Args:
            witness: Witness instance
        """
        self.witnesses.append(witness)
    
    def add_location(self, location):
        """
        Add location to the case.
        
        Args:
            location: Location instance
        """
        self.locations.append(location)
    
    def add_note(self, note):
        """
        Add a note to the case.
        
        Args:
            note: Text note to add
        """
        self.notes.append(note)
    
    def get_evidence_by_id(self, evidence_id):
        """
        Get evidence by ID.
        
        Args:
            evidence_id: Evidence ID to find
            
        Returns:
            Evidence instance or None if not found
        """
        return next((e for e in self.evidence if e.id == evidence_id), None)
    
    def get_suspect_by_name(self, name):
        """
        Get suspect by name.
        
        Args:
            name: Suspect name to find
            
        Returns:
            Suspect instance or None if not found
        """
        return next((s for s in self.suspects if s.name == name), None)
    
    def get_witness_by_name(self, name):
        """
        Get witness by name.
        
        Args:
            name: Witness name to find
            
        Returns:
            Witness instance or None if not found
        """
        return next((w for w in self.witnesses if w.name == name), None)
    
    def get_location_by_name(self, name):
        """
        Get location by name.
        
        Args:
            name: Location name to find
            
        Returns:
            Location instance or None if not found
        """
        return next((l for l in self.locations if l.name == name), None)
    
    def solve(self, suspect):
        """
        Solve the case by accusing a suspect.
        
        Args:
            suspect: Suspect accused of the crime
            
        Returns:
            Boolean indicating if the correct suspect was accused
        """
        self.solved_suspect = suspect
        self.status = "solved"
        
        # Check if the right suspect was accused
        is_correct = suspect == self.actual_culprit
        
        if is_correct:
            logger.info(f"Case '{self.title}' solved correctly!")
        else:
            logger.info(f"Case '{self.title}' solved incorrectly. Accused: {suspect.name}, Actual: {self.actual_culprit.name}")
        
        return is_correct
    
    def close(self):
        """Close the case without solving it."""
        self.status = "closed"
        logger.info(f"Case '{self.title}' closed without solution.")
    
    def is_evidence_discovered(self, evidence_id):
        """
        Check if evidence has been discovered.
        
        Args:
            evidence_id: Evidence ID to check
            
        Returns:
            Boolean indicating if evidence is discovered
        """
        evidence = self.get_evidence_by_id(evidence_id)
        return evidence and evidence.discovered
    
    def get_discovered_evidence(self):
        """Get all discovered evidence."""
        return [e for e in self.evidence if e.discovered]
    
    def get_interviewed_witnesses(self):
        """Get all interviewed witnesses."""
        return [w for w in self.witnesses if w.interviewed]
    
    def get_interrogated_suspects(self):
        """Get all interrogated suspects."""
        return [s for s in self.suspects if s.interrogated]
    
    def get_visited_locations(self):
        """Get all visited locations."""
        return [l for l in self.locations if l.visited]
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'title': self.title,
            'description': self.description,
            'crime_type': self.crime_type,
            'status': self.status,
            'evidence': [e.to_dict() for e in self.evidence],
            'suspects': [s.to_dict() for s in self.suspects],
            'witnesses': [w.to_dict() for w in self.witnesses],
            'locations': [l.to_dict() for l in self.locations],
            'notes': self.notes,
            'current_theory': self.current_theory,
            'solved_suspect': self.solved_suspect.name if self.solved_suspect else None,
            'actual_culprit': self.actual_culprit.name if self.actual_culprit else None,
            'case_file': self.case_file,
            'time_spent': self.time_spent
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        case = cls(
            data['title'],
            data['description'],
            data['crime_type']
        )
        case.status = data['status']
        case.notes = data['notes']
        case.current_theory = data['current_theory']
        case.case_file = data['case_file']
        case.time_spent = data['time_spent']
        
        # Restore evidence
        for evidence_data in data['evidence']:
            case.evidence.append(Evidence.from_dict(evidence_data))
        
        # Restore witnesses
        for witness_data in data['witnesses']:
            case.witnesses.append(Witness.from_dict(witness_data))
        
        # Restore locations
        for location_data in data['locations']:
            case.locations.append(Location.from_dict(location_data))
        
        # Restore suspects
        for suspect_data in data['suspects']:
            case.suspects.append(Suspect.from_dict(suspect_data, case.evidence))
        
        # Restore solved suspect and actual culprit
        if data['solved_suspect']:
            case.solved_suspect = case.get_suspect_by_name(data['solved_suspect'])
        
        if data['actual_culprit']:
            case.actual_culprit = case.get_suspect_by_name(data['actual_culprit'])
        
        return case

class CaseGenerator:
    """Generates procedural detective cases."""
    
    def __init__(self):
        """Initialize the case generator."""
        # Crime types
        self.crime_types = [
            "Murder", "Theft", "Burglary", "Assault", "Kidnapping", 
            "Fraud", "Arson", "Vandalism", "Blackmail"
        ]
        
        # Motives
        self.motives = [
            "Revenge", "Greed", "Jealousy", "Love", "Hatred", 
            "Fear", "Power", "Necessity", "Accident"
        ]
        
        # Locations
        self.location_types = [
            "House", "Apartment", "Office", "Warehouse", "Alley", 
            "Park", "Restaurant", "Hotel", "Store", "Factory"
        ]
        
        # Evidence types and names
        self.evidence_templates = {
            EvidenceType.PHYSICAL: [
                "Bloody Knife", "Broken Glass", "Footprint", "Fingerprint", "Hair Sample",
                "Torn Clothing", "Bullet Casing", "Lock Pick", "Stolen Item", "Weapon"
            ],
            EvidenceType.TESTIMONY: [
                "Eyewitness Account", "Victim Statement", "Suspect Interview", "Neighbor's Testimony",
                "Alibi Testimony", "Confession", "Anonymous Tip", "Character Witness", "Expert Testimony"
            ],
            EvidenceType.DOCUMENT: [
                "Will", "Contract", "Letter", "Email", "Text Message", "Note", "Receipt",
                "Bank Statement", "Legal Document", "Diary Entry"
            ],
            EvidenceType.PHOTO: [
                "Crime Scene Photo", "Security Camera Footage", "Photo of Suspect", "Photo of Victim",
                "Satellite Image", "Traffic Camera Photo", "Social Media Photo", "ID Photo"
            ],
            EvidenceType.FORENSIC: [
                "DNA Sample", "Blood Type Analysis", "Toxicology Report", "Ballistics Report",
                "Autopsy Report", "Fiber Analysis", "Digital Forensics", "Chemical Analysis"
            ]
        }
        
        # Names for generating characters
        self.first_names = [
            "John", "Michael", "David", "James", "Robert", "William", "Thomas", "Daniel",
            "Mary", "Jennifer", "Linda", "Patricia", "Elizabeth", "Susan", "Jessica", "Sarah",
            "Alex", "Sam", "Jamie", "Taylor", "Morgan", "Jordan", "Casey", "Riley"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
            "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
            "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis", "Lee"
        ]
        
        # Job titles for character descriptions
        self.jobs = [
            "Teacher", "Doctor", "Lawyer", "Accountant", "Engineer", "Chef", "Artist",
            "Writer", "Police Officer", "Firefighter", "Nurse", "Scientist", "Mechanic",
            "Electrician", "Carpenter", "Plumber", "Janitor", "Waiter", "Cashier", "Manager"
        ]
    
    def _generate_name(self):
        """Generate a random name."""
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        return f"{first_name} {last_name}"
    
    def _generate_description(self):
        """Generate a character description."""
        age = random.randint(20, 70)
        job = random.choice(self.jobs)
        return f"A {age}-year-old {job}."
    
    def _generate_alibi(self):
        """Generate a random alibi."""
        alibis = [
            "Was at home alone",
            "Was at work",
            "Was with friends at a restaurant",
            "Was at the movies",
            "Was visiting family",
            "Was out of town",
            "Was at the gym",
            "Was at a bar",
            "Claims to have been asleep",
            "Says they were shopping"
        ]
        return random.choice(alibis)
    
    def _generate_evidence(self, case, location_names, suspect_names, evidence_count=10):
        """
        Generate evidence for a case.
        
        Args:
            case: Case to generate evidence for
            location_names: List of location names
            suspect_names: List of suspect names
            evidence_count: Number of evidence pieces to generate
            
        Returns:
            List of generated Evidence instances
        """
        evidence_list = []
        
        # Generate evidence of different types
        for i in range(evidence_count):
            # Choose evidence type
            evidence_type = random.choice(list(EvidenceType))
            
            # Choose evidence name from template
            evidence_name = random.choice(self.evidence_templates[evidence_type])
            
            # Generate description
            if evidence_type == EvidenceType.PHYSICAL:
                description = f"A {evidence_name.lower()} found at the scene."
            elif evidence_type == EvidenceType.TESTIMONY:
                description = f"A {evidence_name.lower()} regarding the case."
            elif evidence_type == EvidenceType.DOCUMENT:
                description = f"A {evidence_name.lower()} related to the case."
            elif evidence_type == EvidenceType.PHOTO:
                description = f"A {evidence_name.lower()} showing relevant details."
            elif evidence_type == EvidenceType.FORENSIC:
                description = f"A {evidence_name.lower()} from forensic analysis."
            
            # Choose location
            location = random.choice(location_names)
            
            # Choose related suspects (0-2)
            related_count = random.randint(0, 2)
            related_suspects = random.sample(suspect_names, min(related_count, len(suspect_names)))
            
            # Create evidence
            evidence = Evidence(
                f"evidence_{i}",
                evidence_name,
                description,
                evidence_type,
                location,
                related_suspects
            )
            
            evidence_list.append(evidence)
            case.add_evidence(evidence)
            
            # Add evidence to location
            location_obj = case.get_location_by_name(location)
            if location_obj:
                location_obj.evidence_ids.append(evidence.id)
        
        return evidence_list
    
    def _generate_locations(self, case, count=5):
        """
        Generate locations for a case.
        
        Args:
            case: Case to generate locations for
            count: Number of locations to generate
            
        Returns:
            List of location names
        """
        location_names = []
        
        for i in range(count):
            # Generate location
            location_type = random.choice(self.location_types)
            name = f"{location_type} {i+1}"
            description = f"A {location_type.lower()} related to the case."
            
            location = Location(name, description)
            case.add_location(location)
            location_names.append(name)
        
        return location_names
    
    def _generate_suspects(self, case, count=4):
        """
        Generate suspects for a case.
        
        Args:
            case: Case to generate suspects for
            count: Number of suspects to generate
            
        Returns:
            List of suspect names and the actual culprit
        """
        suspect_names = []
        
        # Generate each suspect
        for i in range(count):
            name = self._generate_name()
            description = self._generate_description()
            alibi = self._generate_alibi()
            motive = random.choice(self.motives) if random.random() < 0.7 else None
            
            # Randomly assign guilt levels
            # One suspect will be the culprit with high guilt
            # Others will have low or medium guilt
            guilt_level = random.randint(0, 30)  # Most are innocent or low guilt
            
            suspect = Suspect(name, description, motive, alibi, guilt_level)
            case.add_suspect(suspect)
            suspect_names.append(name)
        
        # Choose one suspect to be the culprit
        culprit_index = random.randint(0, count - 1)
        culprit = case.suspects[culprit_index]
        culprit.guilt_level = random.randint(80, 100)  # High guilt
        
        # Make sure culprit has a motive
        if not culprit.motive:
            culprit.motive = random.choice(self.motives)
        
        case.actual_culprit = culprit
        
        return suspect_names, culprit
    
    def _generate_witnesses(self, case, count=3):
        """
        Generate witnesses for a case.
        
        Args:
            case: Case to generate witnesses for
            count: Number of witnesses to generate
        """
        for i in range(count):
            name = self._generate_name()
            description = self._generate_description()
            
            # Generate testimony
            testimony_templates = [
                "I saw someone running from the scene.",
                "I heard a loud noise around the time of the incident.",
                "I noticed something suspicious earlier that day.",
                "I was nearby and saw a person matching the description.",
                "I witnessed an argument before the incident."
            ]
            
            testimony = random.choice(testimony_templates)
            
            # Add suspect name to testimony sometimes
            if random.random() < 0.5 and case.suspects:
                suspect = random.choice(case.suspects)
                testimony += f" I think it might have been {suspect.name}."
            
            witness = Witness(name, description, testimony)
            case.add_witness(witness)
    
    def _connect_evidence_to_culprit(self, case, culprit):
        """
        Connect some evidence to the actual culprit.
        
        Args:
            case: Case instance
            culprit: Culprit Suspect instance
        """
        # Ensure at least 2-3 pieces of evidence point to the culprit
        evidence_count = len(case.evidence)
        clue_count = min(evidence_count, random.randint(2, 3))
        
        # Choose random evidence to connect to culprit
        key_evidence = random.sample(case.evidence, clue_count)
        
        for evidence in key_evidence:
            if culprit.name not in evidence.related_suspects:
                evidence.related_suspects.append(culprit.name)
            
            # Make the description more incriminating
            evidence.description += f" This seems to implicate {culprit.name}."
    
    def generate_case(self, difficulty=1):
        """
        Generate a complete detective case.
        
        Args:
            difficulty: Difficulty level (1-10)
            
        Returns:
            Newly generated Case instance
        """
        # Choose crime type
        crime_type = random.choice(self.crime_types)
        
        # Generate case title and description
        title = f"The Case of the {random.choice(['Mysterious', 'Puzzling', 'Strange', 'Unexpected'])} {crime_type}"
        description = f"A {crime_type.lower()} case that requires investigation."
        
        # Create base case
        case = Case(title, description, crime_type)
        
        # Generate locations, suspects, and witnesses
        location_count = 3 + difficulty // 2
        suspect_count = 3 + difficulty // 3
        witness_count = 2 + difficulty // 3
        evidence_count = 5 + difficulty
        
        # Generate components
        location_names = self._generate_locations(case, location_count)
        suspect_names, culprit = self._generate_suspects(case, suspect_count)
        self._generate_witnesses(case, witness_count)
        self._generate_evidence(case, location_names, suspect_names, evidence_count)
        
        # Connect evidence to culprit
        self._connect_evidence_to_culprit(case, culprit)
        
        logger.info(f"Generated case: {title} with {location_count} locations, {suspect_count} suspects, {witness_count} witnesses, and {evidence_count} evidence")
        
        return case

class InvestigationState(GameState):
    """
    Game state for crime noir investigation gameplay.
    
    This state handles:
    - Detective gameplay focused on solving crimes
    - Clue collection and evidence gathering
    - Witness questioning with dialog options
    - Suspect tracking and arrest mechanics
    """
    
    def __init__(self, state_manager, event_bus, settings):
        """Initialize the investigation state."""
        super().__init__(state_manager, event_bus, settings)
        
        # Current case
        self.current_case = None
        
        # UI state
        self.current_view = "case_board"  # case_board, location, interview, evidence, notes
        self.selected_item = None
        self.dialog_options = []
        self.dialog_responses = []
        
        # UI elements
        self.font_small = None
        self.font_medium = None
        self.font_large = None
        self.colors = {
            'background': (40, 40, 50),
            'text': (220, 220, 220),
            'highlight': (100, 150, 200),
            'button': (60, 60, 80),
            'button_hover': (80, 80, 100),
            'evidence': (200, 180, 100),
            'suspect': (200, 100, 100),
            'witness': (100, 200, 100),
            'location': (150, 150, 200),
            'note': (180, 180, 150)
        }
        
        # Time tracking
        self.investigation_time = 0  # Time spent investigating (in-game hours)
        self.time_limit = 72  # Time limit in hours
        
        # Case generation
        self.case_generator = CaseGenerator()
        
        logger.info("InvestigationState initialized")
    
    def enter(self, data=None):
        """Set up the state when entered."""
        super().enter(data)
        
        # Initialize fonts
        pygame.font.init()
        self.font_small = pygame.font.SysFont(None, 18)
        self.font_medium = pygame.font.SysFont(None, 24)
        self.font_large = pygame.font.SysFont(None, 36)
        
        # If case is provided in data, use it
        if data and "case" in data:
            self.current_case = data["case"]
            logger.info(f"Loaded existing case: {self.current_case.title}")
        else:
            # Generate a new case
            difficulty = data.get("difficulty", 1) if data else 1
            self.current_case = self.case_generator.generate_case(difficulty)
            logger.info(f"Generated new case: {self.current_case.title}")
        
        # Reset UI state
        self.current_view = "case_board"
        self.selected_item = None
        self.investigation_time = 0
        
        logger.info("Entered investigation state")
    
    def exit(self):
        """Clean up when leaving the state."""
        # Store current case in persistent data
        self.state_manager.set_persistent_data("current_case", self.current_case)
        
        super().exit()
        logger.info("Exited investigation state")
    
    def handle_event(self, event):
        """Handle pygame events."""
        if not self.active:
            return
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Handle mouse clicks based on current view
            self._handle_mouse_click(event.pos)
        
        elif event.type == pygame.KEYDOWN:
            # Handle keyboard input
            if event.key == pygame.K_ESCAPE:
                # Return to case board from any view
                if self.current_view != "case_board":
                    self.current_view = "case_board"
                    self.selected_item = None
                else:
                    # Exit investigation mode
                    self._exit_investigation()
            
            elif event.key == pygame.K_b:
                # Shortcut to case board
                self.current_view = "case_board"
                self.selected_item = None
            
            elif event.key == pygame.K_n:
                # Shortcut to notes
                self.current_view = "notes"
            
            elif event.key == pygame.K_e:
                # Shortcut to evidence
                self.current_view = "evidence"
            
            elif event.key == pygame.K_s:
                # Shortcut to suspects
                self.current_view = "suspects"
            
            elif event.key == pygame.K_l:
                # Shortcut to locations
                self.current_view = "locations"
            
            elif event.key == pygame.K_w:
                # Shortcut to witnesses
                self.current_view = "witnesses"
    
    def update(self, dt):
        """Update game state."""
        if not self.active:
            return
        
        # Update in-game time (1 real second = 1 in-game minute)
        self.investigation_time += dt / 60
        
        # Update case time
        if self.current_case:
            self.current_case.time_spent = self.investigation_time
        
        # Check for time limit (if enabled)
        if self.time_limit > 0 and self.investigation_time >= self.time_limit:
            self._time_expired()
    
    def render(self, screen):
        """Render the game state."""
        if not self.visible:
            return
        
        # Fill background
        screen.fill(self.colors['background'])
        
        # Render current view
        if self.current_view == "case_board":
            self._render_case_board(screen)
        elif self.current_view == "location":
            self._render_location_view(screen)
        elif self.current_view == "interview":
            self._render_interview_view(screen)
        elif self.current_view == "evidence":
            self._render_evidence_view(screen)
        elif self.current_view == "notes":
            self._render_notes_view(screen)
        elif self.current_view == "suspects":
            self._render_suspects_view(screen)
        elif self.current_view == "witnesses":
            self._render_witnesses_view(screen)
        elif self.current_view == "locations":
            self._render_locations_view(screen)
        
        # Render time indicator
        self._render_time_indicator(screen)
    
    def _handle_mouse_click(self, pos):
        """
        Handle mouse click at position.
        
        Args:
            pos: (x, y) mouse position
        """
        # Different handling based on current view
        if self.current_view == "case_board":
            self._handle_case_board_click(pos)
        elif self.current_view == "location":
            self._handle_location_click(pos)
        elif self.current_view == "interview":
            self._handle_interview_click(pos)
        elif self.current_view == "evidence":
            self._handle_evidence_click(pos)
        elif self.current_view == "notes":
            self._handle_notes_click(pos)
        elif self.current_view == "suspects":
            self._handle_suspects_click(pos)
        elif self.current_view == "witnesses":
            self._handle_witnesses_click(pos)
        elif self.current_view == "locations":
            self._handle_locations_click(pos)
    
    def _handle_case_board_click(self, pos):
        """
        Handle clicks on the case board.
        
        Args:
            pos: (x, y) mouse position
        """
        # Case board has buttons for different views
        x, y = pos
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        # Check buttons at bottom of screen
        button_height = 50
        button_y = screen_height - button_height - 10
        button_width = (screen_width - 60) // 5
        
        # Evidence button
        if 10 <= x < 10 + button_width and button_y <= y < button_y + button_height:
            self.current_view = "evidence"
        
        # Suspects button
        elif 20 + button_width <= x < 20 + 2*button_width and button_y <= y < button_y + button_height:
            self.current_view = "suspects"
        
        # Witnesses button
        elif 30 + 2*button_width <= x < 30 + 3*button_width and button_y <= y < button_y + button_height:
            self.current_view = "witnesses"
        
        # Locations button
        elif 40 + 3*button_width <= x < 40 + 4*button_width and button_y <= y < button_y + button_height:
            self.current_view = "locations"
        
        # Notes button
        elif 50 + 4*button_width <= x < 50 + 5*button_width and button_y <= y < button_y + button_height:
            self.current_view = "notes"
        
        # Check for solve case button
        solve_button_rect = pygame.Rect(screen_width - 150, 20, 130, 40)
        if solve_button_rect.collidepoint(pos):
            self._show_solve_dialog()
    
    def _handle_location_click(self, pos):
        """
        Handle clicks in location view.
        
        Args:
            pos: (x, y) mouse position
        """
        location = self.selected_item
        if not location:
            return
        
        # Check for search button
        x, y = pos
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        search_button_rect = pygame.Rect(screen_width // 2 - 75, screen_height - 100, 150, 40)
        if search_button_rect.collidepoint(pos):
            self._search_location(location)
            
            # After searching, update time
            self.investigation_time += 1.0  # Searching takes 1 hour
    
    def _handle_evidence_click(self, pos):
        """
        Handle clicks in evidence view.
        
        Args:
            pos: (x, y) mouse position
        """
        # Check if clicked on an evidence item
        for i, evidence in enumerate(self.current_case.evidence):
            if not evidence.discovered:
                continue
                
            # Calculate evidence item rectangle
            x, y = pos
            screen_width = pygame.display.get_surface().get_size()[0]
            
            item_width = (screen_width - 60) // 3
            item_height = 80
            
            row = i // 3
            col = i % 3
            
            item_x = 20 + col * (item_width + 10)
            item_y = 100 + row * (item_height + 10)
            
            item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
            
            if item_rect.collidepoint(pos):
                # Select evidence
                self.selected_item = evidence
                
                # Analyze evidence if not already analyzed
                if not evidence.analyzed:
                    self._analyze_evidence(evidence)
                    
                    # Analyzing takes time
                    self.investigation_time += 0.5  # 30 minutes
    
    def _handle_interview_click(self, pos):
        """
        Handle clicks in interview view.
        
        Args:
            pos: (x, y) mouse position
        """
        # Check if clicked on a dialog option
        interviewee = self.selected_item
        if not interviewee:
            return
            
        x, y = pos
        screen_height = pygame.display.get_surface().get_size()[1]
        
        # Dialog options start at bottom of screen
        option_height = 50
        option_y_start = screen_height - (len(self.dialog_options) * option_height) - 20
        
        for i, option in enumerate(self.dialog_options):
            option_y = option_y_start + i * option_height
            option_rect = pygame.Rect(20, option_y, 760, option_height)
            
            if option_rect.collidepoint(pos):
                # Select dialog option
                self._select_dialog_option(i)
                
                # Talking takes time
                self.investigation_time += 0.25  # 15 minutes
    
    def _handle_notes_click(self, pos):
        """
        Handle clicks in notes view.
        
        Args:
            pos: (x, y) mouse position
        """
        # Check if clicked add note button
        x, y = pos
        screen_width, screen_height = pygame.display.get_surface().get_size()
        
        add_note_rect = pygame.Rect(screen_width - 150, screen_height - 50, 130, 40)
        if add_note_rect.collidepoint(pos):
            self._add_note()
    
    def _handle_suspects_click(self, pos):
        """
        Handle clicks in suspects view.
        
        Args:
            pos: (x, y) mouse position
        """
        # Check if clicked on a suspect
        for i, suspect in enumerate(self.current_case.suspects):
            # Calculate suspect item rectangle
            x, y = pos
            screen_width = pygame.display.get_surface().get_size()[0]
            
            item_width = (screen_width - 60) // 2
            item_height = 100
            
            row = i // 2
            col = i % 2
            
            item_x = 20 + col * (item_width + 20)
            item_y = 100 + row * (item_height + 20)
            
            item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
            
            if item_rect.collidepoint(pos):
                # Select suspect and start interview
                self.selected_item = suspect
                self.current_view = "interview"
                self._start_interview(suspect)
    
    def _handle_witnesses_click(self, pos):
        """
        Handle clicks in witnesses view.
        
        Args:
            pos: (x, y) mouse position
        """
        # Check if clicked on a witness
        for i, witness in enumerate(self.current_case.witnesses):
            # Calculate witness item rectangle
            x, y = pos
            screen_width = pygame.display.get_surface().get_size()[0]
            
            item_width = (screen_width - 60) // 2
            item_height = 100
            
            row = i // 2
            col = i % 2
            
            item_x = 20 + col * (item_width + 20)
            item_y = 100 + row * (item_height + 20)
            
            item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
            
            if item_rect.collidepoint(pos):
                # Select witness and start interview
                self.selected_item = witness
                self.current_view = "interview"
                self._start_interview(witness)
    
    def _handle_locations_click(self, pos):
        """
        Handle clicks in locations view.
        
        Args:
            pos: (x, y) mouse position
        """
        # Check if clicked on a location
        for i, location in enumerate(self.current_case.locations):
            # Calculate location item rectangle
            x, y = pos
            screen_width = pygame.display.get_surface().get_size()[0]
            
            item_width = (screen_width - 60) // 2
            item_height = 100
            
            row = i // 2
            col = i % 2
            
            item_x = 20 + col * (item_width + 20)
            item_y = 100 + row * (item_height + 20)
            
            item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
            
            if item_rect.collidepoint(pos):
                # Select location and go to location view
                self.selected_item = location
                self.current_view = "location"
                
                # Mark as visited
                if not location.visited:
                    location.visit()
                    
                    # Traveling takes time
                    self.investigation_time += 0.5  # 30 minutes
    
    def _render_case_board(self, screen):
        """
        Render the main case board.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Draw case title and information
        title_text = self.font_large.render(f"CASE: {self.current_case.title}", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        description_text = self.font_medium.render(self.current_case.description, True, self.colors['text'])
        screen.blit(description_text, (20, 70))
        
        # Solve case button
        solve_button_rect = pygame.Rect(screen_width - 150, 20, 130, 40)
        pygame.draw.rect(screen, self.colors['button'], solve_button_rect)
        pygame.draw.rect(screen, self.colors['highlight'], solve_button_rect, 2)
        
        solve_text = self.font_medium.render("Solve Case", True, self.colors['text'])
        text_rect = solve_text.get_rect(center=solve_button_rect.center)
        screen.blit(solve_text, text_rect)
        
        # Draw case status
        status_text = self.font_medium.render(f"Status: {self.current_case.status.upper()}", True, self.colors['text'])
        screen.blit(status_text, (20, 100))
        
        # Draw case statistics
        stats_y = 140
        stats = [
            f"Evidence: {len(self.current_case.get_discovered_evidence())}/{len(self.current_case.evidence)}",
            f"Suspects: {len(self.current_case.get_interrogated_suspects())}/{len(self.current_case.suspects)}",
            f"Witnesses: {len(self.current_case.get_interviewed_witnesses())}/{len(self.current_case.witnesses)}",
            f"Locations: {len(self.current_case.get_visited_locations())}/{len(self.current_case.locations)}"
        ]
        
        for i, stat in enumerate(stats):
            stat_text = self.font_medium.render(stat, True, self.colors['text'])
            screen.blit(stat_text, (20, stats_y + i * 30))
        
        # Current theory box
        theory_y = 280
        pygame.draw.rect(screen, self.colors['button'], (20, theory_y, screen_width - 40, 150))
        pygame.draw.rect(screen, self.colors['highlight'], (20, theory_y, screen_width - 40, 150), 2)
        
        theory_title = self.font_medium.render("Current Theory", True, self.colors['text'])
        screen.blit(theory_title, (30, theory_y + 10))
        
        theory_text = self.font_medium.render(
            self.current_case.current_theory if self.current_case.current_theory else "No theory yet...",
            True, self.colors['text']
        )
        screen.blit(theory_text, (30, theory_y + 40))
        
        # Bottom buttons
        button_height = 50
        button_y = screen_height - button_height - 10
        button_width = (screen_width - 60) // 5
        
        buttons = ["Evidence", "Suspects", "Witnesses", "Locations", "Notes"]
        button_colors = [
            self.colors['evidence'],
            self.colors['suspect'],
            self.colors['witness'],
            self.colors['location'],
            self.colors['note']
        ]
        
        for i, text in enumerate(buttons):
            button_x = 10 + i * (button_width + 10)
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            
            pygame.draw.rect(screen, button_colors[i], button_rect)
            pygame.draw.rect(screen, self.colors['highlight'], button_rect, 2)
            
            button_text = self.font_medium.render(text, True, self.colors['text'])
            text_rect = button_text.get_rect(center=button_rect.center)
            screen.blit(button_text, text_rect)
    
    def _render_location_view(self, screen):
        """
        Render the location view.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        location = self.selected_item
        if not location:
            # If no location selected, return to case board
            self.current_view = "case_board"
            return
        
        # Draw location name
        title_text = self.font_large.render(f"LOCATION: {location.name}", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        # Draw description
        description_text = self.font_medium.render(location.description, True, self.colors['text'])
        screen.blit(description_text, (20, 70))
        
        # Draw status
        status_text = self.font_medium.render(
            f"Status: {'Searched' if location.searched else 'Not searched'}",
            True, self.colors['text']
        )
        screen.blit(status_text, (20, 110))
        
        # Draw evidence found
        evidence_y = 150
        evidence_title = self.font_medium.render("Evidence Found:", True, self.colors['text'])
        screen.blit(evidence_title, (20, evidence_y))
        
        if location.searched:
            # List evidence found at this location
            evidence_items = [
                self.current_case.get_evidence_by_id(evidence_id)
                for evidence_id in location.evidence_ids
                if self.current_case.is_evidence_discovered(evidence_id)
            ]
            
            if evidence_items:
                for i, evidence in enumerate(evidence_items):
                    evidence_text = self.font_medium.render(
                        f"- {evidence.name}: {evidence.description}",
                        True, self.colors['evidence']
                    )
                    screen.blit(evidence_text, (40, evidence_y + 30 + i * 30))
            else:
                no_evidence_text = self.font_medium.render("No evidence found", True, self.colors['text'])
                screen.blit(no_evidence_text, (40, evidence_y + 30))
        else:
            not_searched_text = self.font_medium.render("Location not yet searched", True, self.colors['text'])
            screen.blit(not_searched_text, (40, evidence_y + 30))
        
        # Draw search button if not searched
        if not location.searched:
            search_button_rect = pygame.Rect(screen_width // 2 - 75, screen_height - 100, 150, 40)
            pygame.draw.rect(screen, self.colors['button'], search_button_rect)
            pygame.draw.rect(screen, self.colors['highlight'], search_button_rect, 2)
            
            search_text = self.font_medium.render("Search Location", True, self.colors['text'])
            text_rect = search_text.get_rect(center=search_button_rect.center)
            screen.blit(search_text, text_rect)
        
        # Draw back button
        back_text = self.font_medium.render("Press ESC to return to case board", True, self.colors['text'])
        screen.blit(back_text, (20, screen_height - 40))
    
    def _render_interview_view(self, screen):
        """
        Render the interview/interrogation view.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        interviewee = self.selected_item
        if not interviewee:
            # If no interviewee selected, return to case board
            self.current_view = "case_board"
            return
        
        # Determine if suspect or witness
        is_suspect = hasattr(interviewee, 'guilt_level')
        
        # Draw interviewee name
        title_prefix = "SUSPECT" if is_suspect else "WITNESS"
        title_text = self.font_large.render(f"{title_prefix}: {interviewee.name}", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        # Draw description
        description_text = self.font_medium.render(interviewee.description, True, self.colors['text'])
        screen.blit(description_text, (20, 70))
        
        # Draw status
        status_text = self.font_medium.render(
            f"Status: {'Interrogated' if is_suspect and interviewee.interrogated else 'Interviewed' if not is_suspect and interviewee.interviewed else 'Not interviewed'}",
            True, self.colors['text']
        )
        screen.blit(status_text, (20, 110))
        
        # Draw dialog history
        dialog_y = 150
        dialog_title = self.font_medium.render("Dialog:", True, self.colors['text'])
        screen.blit(dialog_title, (20, dialog_y))
        
        # Draw dialog responses (if any)
        response_y = dialog_y + 30
        for i, response in enumerate(self.dialog_responses):
            # Wrap text to fit screen
            words = response.split(' ')
            lines = []
            line = ""
            
            for word in words:
                test_line = line + " " + word if line else word
                if self.font_medium.size(test_line)[0] < screen_width - 40:
                    line = test_line
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
            
            # Draw each line
            for j, line_text in enumerate(lines):
                line_surface = self.font_medium.render(line_text, True, self.colors['text'])
                screen.blit(line_surface, (40, response_y + (i * 60) + (j * 30)))
            
            response_y += len(lines) * 30
        
        # Draw dialog options
        option_height = 50
        option_y_start = screen_height - (len(self.dialog_options) * option_height) - 20
        
        for i, option in enumerate(self.dialog_options):
            option_y = option_y_start + i * option_height
            option_rect = pygame.Rect(20, option_y, screen_width - 40, option_height)
            
            pygame.draw.rect(screen, self.colors['button'], option_rect)
            pygame.draw.rect(screen, self.colors['highlight'], option_rect, 2)
            
            option_text = self.font_medium.render(option, True, self.colors['text'])
            screen.blit(option_text, (30, option_y + 15))
        
        # Draw back button
        back_text = self.font_small.render("Press ESC to return to case board", True, self.colors['text'])
        screen.blit(back_text, (20, screen_height - len(self.dialog_options) * option_height - 40))
    
    def _render_evidence_view(self, screen):
        """
        Render the evidence collection view.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Draw title
        title_text = self.font_large.render("EVIDENCE", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        # Draw evidence count
        count_text = self.font_medium.render(
            f"Discovered: {len(self.current_case.get_discovered_evidence())}/{len(self.current_case.evidence)}",
            True, self.colors['text']
        )
        screen.blit(count_text, (20, 70))
        
        # Draw evidence grid
        grid_y = 100
        item_width = (screen_width - 60) // 3
        item_height = 80
        
        discovered_evidence = self.current_case.get_discovered_evidence()
        
        if discovered_evidence:
            for i, evidence in enumerate(discovered_evidence):
                row = i // 3
                col = i % 3
                
                item_x = 20 + col * (item_width + 10)
                item_y = grid_y + row * (item_height + 10)
                
                # Draw evidence box
                item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
                pygame.draw.rect(screen, self.colors['evidence'], item_rect)
                pygame.draw.rect(screen, self.colors['highlight'], item_rect, 2)
                
                # Draw evidence name
                name_text = self.font_medium.render(evidence.name, True, self.colors['text'])
                screen.blit(name_text, (item_x + 10, item_y + 10))
                
                # Draw evidence type
                type_text = self.font_small.render(
                    f"Type: {evidence.evidence_type.name}",
                    True, self.colors['text']
                )
                screen.blit(type_text, (item_x + 10, item_y + 35))
                
                # Draw analyzed indicator
                analyzed_text = self.font_small.render(
                    "ANALYZED" if evidence.analyzed else "NOT ANALYZED",
                    True, self.colors['text']
                )
                screen.blit(analyzed_text, (item_x + 10, item_y + 55))
        else:
            no_evidence_text = self.font_medium.render("No evidence discovered yet", True, self.colors['text'])
            screen.blit(no_evidence_text, (20, grid_y + 20))
        
        # Draw evidence details if selected
        if self.selected_item and isinstance(self.selected_item, Evidence):
            evidence = self.selected_item
            
            # Draw details box
            details_y = screen_height - 200
            pygame.draw.rect(screen, self.colors['button'], (20, details_y, screen_width - 40, 180))
            pygame.draw.rect(screen, self.colors['highlight'], (20, details_y, screen_width - 40, 180), 2)
            
            # Draw evidence details
            detail_title = self.font_medium.render(f"DETAILS: {evidence.name}", True, self.colors['text'])
            screen.blit(detail_title, (30, details_y + 10))
            
            description_text = self.font_medium.render(
                evidence.description,
                True, self.colors['text']
            )
            screen.blit(description_text, (30, details_y + 40))
            
            location_text = self.font_medium.render(
                f"Found at: {evidence.location}",
                True, self.colors['text']
            )
            screen.blit(location_text, (30, details_y + 70))
            
            if evidence.analyzed:
                # Show related suspects if analyzed
                if evidence.related_suspects:
                    related_text = self.font_medium.render(
                        f"Related suspects: {', '.join(evidence.related_suspects)}",
                        True, self.colors['text']
                    )
                    screen.blit(related_text, (30, details_y + 100))
                else:
                    related_text = self.font_medium.render(
                        "No related suspects identified",
                        True, self.colors['text']
                    )
                    screen.blit(related_text, (30, details_y + 100))
            else:
                analyze_text = self.font_medium.render(
                    "Click to analyze this evidence",
                    True, self.colors['text']
                )
                screen.blit(analyze_text, (30, details_y + 100))
        
        # Draw back button
        back_text = self.font_medium.render("Press ESC to return to case board", True, self.colors['text'])
        screen.blit(back_text, (20, 20 if self.selected_item else screen_height - 40))
    
    def _render_notes_view(self, screen):
        """
        Render the detective notes view.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Draw title
        title_text = self.font_large.render("DETECTIVE NOTES", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        # Draw notes
        notes_y = 70
        
        if self.current_case.notes:
            for i, note in enumerate(self.current_case.notes):
                # Draw note box
                note_rect = pygame.Rect(20, notes_y + i * 60, screen_width - 40, 50)
                pygame.draw.rect(screen, self.colors['note'], note_rect)
                pygame.draw.rect(screen, self.colors['highlight'], note_rect, 2)
                
                # Draw note text
                note_text = self.font_medium.render(note, True, self.colors['text'])
                screen.blit(note_text, (30, notes_y + i * 60 + 15))
        else:
            no_notes_text = self.font_medium.render("No notes yet", True, self.colors['text'])
            screen.blit(no_notes_text, (20, notes_y + 20))
        
        # Draw add note button
        add_note_rect = pygame.Rect(screen_width - 150, screen_height - 50, 130, 40)
        pygame.draw.rect(screen, self.colors['button'], add_note_rect)
        pygame.draw.rect(screen, self.colors['highlight'], add_note_rect, 2)
        
        add_note_text = self.font_medium.render("Add Note", True, self.colors['text'])
        text_rect = add_note_text.get_rect(center=add_note_rect.center)
        screen.blit(add_note_text, text_rect)
        
        # Draw back button
        back_text = self.font_medium.render("Press ESC to return to case board", True, self.colors['text'])
        screen.blit(back_text, (20, screen_height - 40))
    
    def _render_suspects_view(self, screen):
        """
        Render the suspects view.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Draw title
        title_text = self.font_large.render("SUSPECTS", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        # Draw suspect count
        count_text = self.font_medium.render(
            f"Interrogated: {len(self.current_case.get_interrogated_suspects())}/{len(self.current_case.suspects)}",
            True, self.colors['text']
        )
        screen.blit(count_text, (20, 70))
        
        # Draw suspects grid
        grid_y = 100
        item_width = (screen_width - 60) // 2
        item_height = 100
        
        if self.current_case.suspects:
            for i, suspect in enumerate(self.current_case.suspects):
                row = i // 2
                col = i % 2
                
                item_x = 20 + col * (item_width + 20)
                item_y = grid_y + row * (item_height + 20)
                
                # Draw suspect box
                item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
                pygame.draw.rect(screen, self.colors['suspect'], item_rect)
                pygame.draw.rect(screen, self.colors['highlight'], item_rect, 2)
                
                # Draw suspect name
                name_text = self.font_medium.render(suspect.name, True, self.colors['text'])
                screen.blit(name_text, (item_x + 10, item_y + 10))
                
                # Draw suspect description
                description_text = self.font_small.render(
                    suspect.description,
                    True, self.colors['text']
                )
                screen.blit(description_text, (item_x + 10, item_y + 40))
                
                # Draw interrogated indicator
                status_text = self.font_small.render(
                    "INTERROGATED" if suspect.interrogated else "NOT INTERROGATED",
                    True, self.colors['text']
                )
                screen.blit(status_text, (item_x + 10, item_y + 70))
        else:
            no_suspects_text = self.font_medium.render("No suspects identified", True, self.colors['text'])
            screen.blit(no_suspects_text, (20, grid_y + 20))
        
        # Draw back button
        back_text = self.font_medium.render("Press ESC to return to case board", True, self.colors['text'])
        screen.blit(back_text, (20, screen_height - 40))
    
    def _render_witnesses_view(self, screen):
        """
        Render the witnesses view.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Draw title
        title_text = self.font_large.render("WITNESSES", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        # Draw witness count
        count_text = self.font_medium.render(
            f"Interviewed: {len(self.current_case.get_interviewed_witnesses())}/{len(self.current_case.witnesses)}",
            True, self.colors['text']
        )
        screen.blit(count_text, (20, 70))
        
        # Draw witnesses grid
        grid_y = 100
        item_width = (screen_width - 60) // 2
        item_height = 100
        
        if self.current_case.witnesses:
            for i, witness in enumerate(self.current_case.witnesses):
                row = i // 2
                col = i % 2
                
                item_x = 20 + col * (item_width + 20)
                item_y = grid_y + row * (item_height + 20)
                
                # Draw witness box
                item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
                pygame.draw.rect(screen, self.colors['witness'], item_rect)
                pygame.draw.rect(screen, self.colors['highlight'], item_rect, 2)
                
                # Draw witness name
                name_text = self.font_medium.render(witness.name, True, self.colors['text'])
                screen.blit(name_text, (item_x + 10, item_y + 10))
                
                # Draw witness description
                description_text = self.font_small.render(
                    witness.description,
                    True, self.colors['text']
                )
                screen.blit(description_text, (item_x + 10, item_y + 40))
                
                # Draw interviewed indicator
                status_text = self.font_small.render(
                    "INTERVIEWED" if witness.interviewed else "NOT INTERVIEWED",
                    True, self.colors['text']
                )
                screen.blit(status_text, (item_x + 10, item_y + 70))
        else:
            no_witnesses_text = self.font_medium.render("No witnesses identified", True, self.colors['text'])
            screen.blit(no_witnesses_text, (20, grid_y + 20))
        
        # Draw back button
        back_text = self.font_medium.render("Press ESC to return to case board", True, self.colors['text'])
        screen.blit(back_text, (20, screen_height - 40))
    
    def _render_locations_view(self, screen):
        """
        Render the locations view.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Draw title
        title_text = self.font_large.render("LOCATIONS", True, self.colors['text'])
        screen.blit(title_text, (20, 20))
        
        # Draw location count
        count_text = self.font_medium.render(
            f"Visited: {len(self.current_case.get_visited_locations())}/{len(self.current_case.locations)}",
            True, self.colors['text']
        )
        screen.blit(count_text, (20, 70))
        
        # Draw locations grid
        grid_y = 100
        item_width = (screen_width - 60) // 2
        item_height = 100
        
        if self.current_case.locations:
            for i, location in enumerate(self.current_case.locations):
                row = i // 2
                col = i % 2
                
                item_x = 20 + col * (item_width + 20)
                item_y = grid_y + row * (item_height + 20)
                
                # Draw location box
                item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
                pygame.draw.rect(screen, self.colors['location'], item_rect)
                pygame.draw.rect(screen, self.colors['highlight'], item_rect, 2)
                
                # Draw location name
                name_text = self.font_medium.render(location.name, True, self.colors['text'])
                screen.blit(name_text, (item_x + 10, item_y + 10))
                
                # Draw location description
                description_text = self.font_small.render(
                    location.description,
                    True, self.colors['text']
                )
                screen.blit(description_text, (item_x + 10, item_y + 40))
                
                # Draw status indicators
                status_text = self.font_small.render(
                    f"{'Visited' if location.visited else 'Not Visited'} | {'Searched' if location.searched else 'Not Searched'}",
                    True, self.colors['text']
                )
                screen.blit(status_text, (item_x + 10, item_y + 70))
        else:
            no_locations_text = self.font_medium.render("No locations identified", True, self.colors['text'])
            screen.blit(no_locations_text, (20, grid_y + 20))
        
        # Draw back button
        back_text = self.font_medium.render("Press ESC to return to case board", True, self.colors['text'])
        screen.blit(back_text, (20, screen_height - 40))
    
    def _render_time_indicator(self, screen):
        """
        Render the time indicator.
        
        Args:
            screen: Pygame surface to render to
        """
        # Get screen dimensions
        screen_width, screen_height = screen.get_size()
        
        # Calculate remaining time if time limit is enabled
        if self.time_limit > 0:
            remaining_time = max(0, self.time_limit - self.investigation_time)
            hours = int(remaining_time)
            minutes = int((remaining_time - hours) * 60)
            
            time_text = self.font_medium.render(
                f"Time Remaining: {hours:02d}:{minutes:02d}",
                True, self.colors['text']
            )
        else:
            # Just show elapsed time
            hours = int(self.investigation_time)
            minutes = int((self.investigation_time - hours) * 60)
            
            time_text = self.font_medium.render(
                f"Investigation Time: {hours:02d}:{minutes:02d}",
                True, self.colors['text']
            )
        
        # Draw time text in top-right corner
        text_rect = time_text.get_rect(topright=(screen_width - 20, 20))
        screen.blit(time_text, text_rect)
    
    def _search_location(self, location):
        """
        Search a location for evidence.
        
        Args:
            location: Location to search
        """
        if location.searched:
            return
        
        # Mark as searched
        location.search()
        
        # Discover evidence
        discovered = []
        for evidence_id in location.evidence_ids:
            evidence = self.current_case.get_evidence_by_id(evidence_id)
            if evidence and not evidence.discovered:
                evidence.discover()
                discovered.append(evidence.name)
        
        # Log discovery
        logger.info(f"Searched location {location.name}, found {len(discovered)} evidence items")
        
        # TODO: Show a notification or dialog about what was found
    
    def _analyze_evidence(self, evidence):
        """
        Analyze a piece of evidence.
        
        Args:
            evidence: Evidence to analyze
        """
        if evidence.analyzed:
            return
        
        # Mark as analyzed
        evidence.analyze()
        
        logger.info(f"Analyzed evidence: {evidence.name}")
        
        # TODO: Show a notification about analysis results
    
    def _start_interview(self, interviewee):
        """
        Start an interview with a suspect or witness.
        
        Args:
            interviewee: Suspect or Witness to interview
        """
        is_suspect = hasattr(interviewee, 'guilt_level')
        
        # Mark as interviewed
        if is_suspect:
            interviewee.interrogate()
        else:
            interviewee.interview()
        
        # Reset dialog
        self.dialog_responses = []
        
        # Add greeting
        if is_suspect:
            if interviewee.interrogated:
                self.dialog_responses.append(f"{interviewee.name}: What do you want now, detective?")
            else:
                self.dialog_responses.append(f"{interviewee.name}: I didn't do anything wrong, detective.")
        else:
            if interviewee.interviewed:
                self.dialog_responses.append(f"{interviewee.name}: Do you have more questions, detective?")
            else:
                self.dialog_responses.append(f"{interviewee.name}: How can I help with your investigation?")
        
        # Set up dialog options
        self._setup_dialog_options(interviewee)
        
        logger.info(f"Started interview with {'suspect' if is_suspect else 'witness'} {interviewee.name}")
    
    def _setup_dialog_options(self, interviewee):
        """
        Set up dialog options for an interview.
        
        Args:
            interviewee: Suspect or Witness being interviewed
        """
        is_suspect = hasattr(interviewee, 'guilt_level')
        
        self.dialog_options = []
        
        # Add basic questions
        if is_suspect:
            # Suspect questions
            self.dialog_options.append("Can you tell me where you were during the incident?")
            
            if interviewee.motive:
                self.dialog_options.append(f"Why would you have a motive of {interviewee.motive}?")
            
            if interviewee.alibi:
                self.dialog_options.append(f"Is it true that you {interviewee.alibi.lower()}?")
            
            # Add evidence-based questions
            for evidence in self.current_case.get_discovered_evidence():
                if evidence.analyzed and interviewee.name in evidence.related_suspects:
                    self.dialog_options.append(f"How do you explain this {evidence.name}?")
        else:
            # Witness questions
            self.dialog_options.append("Can you tell me what you saw?")
            
            if interviewee.testimony:
                self.dialog_options.append("Can you elaborate on your previous statement?")
            
            # Add suspect-related questions
            for suspect in self.current_case.suspects:
                self.dialog_options.append(f"Did you see {suspect.name} around the time of the incident?")
        
        # Add generic options
        self.dialog_options.append("I need to think about this. Let's talk later.")
    
    def _select_dialog_option(self, option_index):
        """
        Select a dialog option.
        
        Args:
            option_index: Index of selected option
        """
        if option_index < 0 or option_index >= len(self.dialog_options):
            return
        
        selected_option = self.dialog_options[option_index]
        interviewee = self.selected_item
        
        if not interviewee:
            return
        
        # Add player question to dialog
        self.dialog_responses.append(f"Detective: {selected_option}")
        
        # Generate response based on option
        is_suspect = hasattr(interviewee, 'guilt_level')
        
        if "Let's talk later" in selected_option:
            # End dialog
            self.dialog_responses.append(f"{interviewee.name}: Fine. You know where to find me.")
            self.current_view = "case_board"
            return
        
        # Generic responses
        if "where you were" in selected_option:
            if is_suspect:
                if interviewee.alibi:
                    self.dialog_responses.append(f"{interviewee.name}: I told you already. {interviewee.alibi}.")
                else:
                    self.dialog_responses.append(f"{interviewee.name}: I don't remember exactly. It was a while ago.")
        
        elif "what you saw" in selected_option:
            if not is_suspect and interviewee.testimony:
                self.dialog_responses.append(f"{interviewee.name}: {interviewee.testimony}")
            else:
                self.dialog_responses.append(f"{interviewee.name}: I'm not sure I saw anything helpful.")
        
        elif "motive" in selected_option:
            if is_suspect:
                if interviewee.guilt_level > 70:  # Guilty
                    self.dialog_responses.append(f"{interviewee.name}: [Nervously] That's ridiculous. I wouldn't do such a thing.")
                else:
                    self.dialog_responses.append(f"{interviewee.name}: I had no reason to commit this crime.")
        
        elif "alibi" in selected_option:
            if is_suspect:
                self.dialog_responses.append(f"{interviewee.name}: Yes, that's correct. You can verify it if you want.")
        
        elif "explain this" in selected_option:
            if is_suspect:
                if interviewee.guilt_level > 70:  # Guilty
                    self.dialog_responses.append(f"{interviewee.name}: [Sweating] I... I don't know anything about that. You're trying to frame me!")
                else:
                    self.dialog_responses.append(f"{interviewee.name}: I have no idea what that has to do with me.")
        
        elif "previous statement" in selected_option:
            if not is_suspect and interviewee.testimony:
                self.dialog_responses.append(f"{interviewee.name}: I've told you everything I know already.")
            else:
                self.dialog_responses.append(f"{interviewee.name}: I'm not sure what else I can add.")
        
        elif "Did you see" in selected_option:
            suspect_name = selected_option.split("Did you see ")[1].split(" around")[0]
            
            if not is_suspect:
                # Random response based on witness reliability
                if random.random() < (interviewee.reliability / 100):
                    saw_suspect = random.choice([True, False])
                    
                    if saw_suspect:
                        self.dialog_responses.append(f"{interviewee.name}: Yes, I think I saw {suspect_name} at the scene.")
                    else:
                        self.dialog_responses.append(f"{interviewee.name}: No, I don't recall seeing {suspect_name} there.")
                else:
                    self.dialog_responses.append(f"{interviewee.name}: I'm not sure. There were several people around.")
        
        # Update dialog options based on new information
        self._setup_dialog_options(interviewee)
    
    def _add_note(self):
        """Add a note to the case."""
        # TODO: Implement proper text input
        # For now, just add a placeholder note
        note = f"Note {len(self.current_case.notes) + 1}: Investigated for {int(self.investigation_time)} hours"
        self.current_case.add_note(note)
        
        logger.info(f"Added note: {note}")
    
    def _show_solve_dialog(self):
        """Show the solve case dialog."""
        # TODO: Implement proper UI dialog
        # For now, just list suspects and ask player to choose
        
        if not self.current_case.suspects:
            return
        
        # For simplicity, just pick the first interrogated suspect
        interrogated_suspects = self.current_case.get_interrogated_suspects()
        
        if not interrogated_suspects:
            # Can't solve without interrogating suspects
            return
        
        suspect = interrogated_suspects[0]
        
        # Solve the case
        is_correct = self.current_case.solve(suspect)
        
        if is_correct:
            # Success!
            self.current_case.status = "solved"
        else:
            # Failure
            self.current_case.status = "closed"
        
        # Exit investigation
        self._exit_investigation()
    
    def _time_expired(self):
        """Handle time expiration."""
        logger.info(f"Investigation time expired after {self.investigation_time} hours")
        
        # Close the case without solving
        self.current_case.close()
        
        # Exit investigation
        self._exit_investigation()
    
    def _exit_investigation(self):
        """Exit investigation mode and return to previous state."""
        logger.info("Exiting investigation")
        
        # Return to police station or world exploration
        self.change_state("world_exploration")
