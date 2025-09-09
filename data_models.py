#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Models for Client Information Extraction
Used for structured data extraction from WhatsApp conversations
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime

class ClientInfo(BaseModel):
    """
    Model for extracting client information from conversations
    Fields are in Italian as per business requirements
    """
    name: Optional[str] = Field(None, description="First name of the client")
    last_name: Optional[str] = Field(None, description="Last name of the client") 
    ragione_sociale: Optional[str] = Field(None, description="Company name (Ragione Sociale)")
    email: Optional[EmailStr] = Field(None, description="Email address")
    
    # Tracking fields
    found_all_info: bool = Field(False, description="Whether all required information has been collected")
    what_is_missing: Optional[str] = Field(None, description="Natural language description of missing information")
    
    @validator('found_all_info', always=True)
    def check_completeness(cls, v, values):
        """Check if all required fields are filled"""
        required_fields = ['name', 'last_name', 'ragione_sociale', 'email']
        all_present = all(values.get(field) is not None for field in required_fields)
        return all_present
    
    @validator('what_is_missing', always=True)
    def determine_missing(cls, v, values):
        """Generate a description of what information is missing"""
        missing = []
        
        if not values.get('name'):
            missing.append('nome')
        if not values.get('last_name'):
            missing.append('cognome')
        if not values.get('ragione_sociale'):
            missing.append('ragione sociale (azienda)')
        if not values.get('email'):
            missing.append('indirizzo email')
        
        if missing:
            if len(missing) == 1:
                return f"Manca ancora: {missing[0]}"
            else:
                return f"Mancano ancora: {', '.join(missing[:-1])} e {missing[-1]}"
        return None
    
    def get_missing_fields_list(self) -> List[str]:
        """Get a list of missing field names"""
        missing = []
        if not self.name:
            missing.append('name')
        if not self.last_name:
            missing.append('last_name')
        if not self.ragione_sociale:
            missing.append('ragione_sociale')
        if not self.email:
            missing.append('email')
        return missing
    
    def get_friendly_request(self) -> Optional[str]:
        """Generate a friendly request for missing information"""
        if self.found_all_info:
            return None
        
        missing = self.get_missing_fields_list()
        
        # Create contextual requests based on what's missing
        if len(missing) == 4:  # Nothing collected yet
            return "Per poterti assistere al meglio, potresti dirmi il tuo nome e cognome, da quale azienda ci contatti e un indirizzo email dove posso inviarti informazioni?"
        
        elif len(missing) == 3:  # Only one field collected
            if self.name:
                return f"Grazie {self.name}! Potresti dirmi anche il tuo cognome, l'azienda per cui lavori e la tua email?"
            elif self.last_name:
                return f"Grazie signor/signora {self.last_name}! Potresti dirmi il tuo nome, l'azienda e un'email di contatto?"
            elif self.ragione_sociale:
                return f"Grazie per averci contattato da {self.ragione_sociale}! Potresti dirmi il tuo nome, cognome e email?"
            elif self.email:
                return "Grazie per l'email! Potresti dirmi anche il tuo nome, cognome e da quale azienda ci contatti?"
        
        elif len(missing) == 2:  # Two fields collected
            requests = []
            if 'name' in missing:
                requests.append('il tuo nome')
            if 'last_name' in missing:
                requests.append('il tuo cognome')
            if 'ragione_sociale' in missing:
                requests.append("l'azienda per cui lavori")
            if 'email' in missing:
                requests.append('la tua email')
            
            return f"Perfetto! Mi mancano solo {' e '.join(requests)}."
        
        elif len(missing) == 1:  # Almost complete
            if 'name' in missing:
                return "Mi manca solo il tuo nome per completare la registrazione."
            elif 'last_name' in missing:
                return "Potresti dirmi il tuo cognome per completare i dati?"
            elif 'ragione_sociale' in missing:
                return "Per quale azienda lavori? Così completo la registrazione."
            elif 'email' in missing:
                return "Mi lasci un'email dove posso inviarti un riepilogo?"
        
        return None
    
    def to_hubspot_format(self) -> dict:
        """Convert to HubSpot contact format"""
        return {
            "properties": {
                "firstname": self.name,
                "lastname": self.last_name,
                "company": self.ragione_sociale,
                "email": self.email,
                "lead_source": "WhatsApp",
                "hs_lead_status": "NEW"
            }
        }
    
    def to_display_string(self) -> str:
        """Create a formatted string for display"""
        parts = []
        if self.name and self.last_name:
            parts.append(f"{self.name} {self.last_name}")
        elif self.name:
            parts.append(self.name)
        elif self.last_name:
            parts.append(f"Sig./Sig.ra {self.last_name}")
        
        if self.ragione_sociale:
            parts.append(f"({self.ragione_sociale})")
        
        if self.email:
            parts.append(f"- {self.email}")
        
        return " ".join(parts) if parts else "Cliente"


class ClientProfile(BaseModel):
    """
    Complete client profile with metadata
    """
    info: ClientInfo
    whatsapp_number: str
    conversation_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    hubspot_synced: bool = False
    hubspot_contact_id: Optional[str] = None
    
    def mark_complete(self):
        """Mark the profile as complete"""
        if self.info.found_all_info:
            self.completed_at = datetime.now()
            self.updated_at = datetime.now()
    
    def mark_synced(self, hubspot_id: str):
        """Mark as synced with HubSpot"""
        self.hubspot_synced = True
        self.hubspot_contact_id = hubspot_id
        self.updated_at = datetime.now()