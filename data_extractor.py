#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Extraction Module
Handles extraction of structured client information from WhatsApp messages
"""

import os
import json
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from data_models import ClientInfo, ClientProfile
from database import db

logger = logging.getLogger(__name__)

class DataExtractor:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize the data extractor
        
        Args:
            api_key: OpenAI API key
            model: Model to use for extraction (default: gpt-4o for structured output)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.profiles: Dict[str, ClientProfile] = {}
        
        # Load existing profiles from database
        self.load_profiles()
        
        logger.info(f"Data Extractor initialized with model: {self.model}")
        logger.info(f"Loaded {len(self.profiles)} existing profiles")
    
    def load_profiles(self):
        """Load existing client profiles from database"""
        try:
            db_profiles = db.get_all_profiles()
            for phone, profile_data in db_profiles.items():
                # Convert database row to ClientInfo
                client_info = ClientInfo(
                    name=profile_data.get('name'),
                    last_name=profile_data.get('last_name'),
                    ragione_sociale=profile_data.get('ragione_sociale'),
                    email=profile_data.get('email'),
                    found_all_info=profile_data.get('found_all_info', False),
                    what_is_missing=None  # Will be recalculated by validator
                )
                
                # Create ClientProfile
                self.profiles[phone] = ClientProfile(
                    info=client_info,
                    whatsapp_number=phone,
                    conversation_id=profile_data.get('conversation_id', ''),
                    created_at=datetime.fromisoformat(profile_data['created_at']) if profile_data.get('created_at') else datetime.now(),
                    updated_at=datetime.fromisoformat(profile_data['updated_at']) if profile_data.get('updated_at') else datetime.now(),
                    completed_at=datetime.fromisoformat(profile_data['completed_at']) if profile_data.get('completed_at') else None,
                    hubspot_synced=profile_data.get('hubspot_synced', False),
                    hubspot_contact_id=profile_data.get('hubspot_contact_id')
                )
            
            logger.info(f"Loaded {len(self.profiles)} client profiles from database")
        except Exception as e:
            logger.error(f"Error loading profiles from database: {e}")
            self.profiles = {}
    
    def save_profiles(self):
        """Save client profiles to database"""
        try:
            for phone, profile in self.profiles.items():
                profile_data = {
                    'name': profile.info.name,
                    'last_name': profile.info.last_name,
                    'ragione_sociale': profile.info.ragione_sociale,
                    'email': profile.info.email,
                    'conversation_id': profile.conversation_id,
                    'hubspot_synced': profile.hubspot_synced,
                    'hubspot_contact_id': profile.hubspot_contact_id
                }
                db.save_profile(phone, profile_data)
            
            logger.debug("Client profiles saved to database")
        except Exception as e:
            logger.error(f"Error saving profiles to database: {e}")
    
    def extract_client_info(self, message: str, current_info: Optional[ClientInfo] = None) -> ClientInfo:
        """
        Extract structured client information from a message
        
        Args:
            message: The user's message text
            current_info: Existing client info to update (if any)
            
        Returns:
            ClientInfo object with extracted data
        """
        try:
            # Build context from existing info
            context = ""
            if current_info:
                if current_info.name:
                    context += f"Nome già noto: {current_info.name}\n"
                if current_info.last_name:
                    context += f"Cognome già noto: {current_info.last_name}\n"
                if current_info.ragione_sociale:
                    context += f"Azienda già nota: {current_info.ragione_sociale}\n"
                if current_info.email:
                    context += f"Email già nota: {current_info.email}\n"
            
            # System prompt for extraction
            system_prompt = f"""Estrai le informazioni del cliente dal messaggio.
Cerca: nome, cognome, ragione sociale (nome azienda), email.
{context}
Mantieni le informazioni già note e aggiungi solo quelle nuove trovate nel messaggio.
Se un'informazione non è presente nel messaggio, lasciala come null.
Imposta found_all_info su true solo se hai TUTTI e 4 i campi.
In what_is_missing, descrivi in italiano cosa manca ancora."""
            
            # Use responses.parse for structured extraction (new API)
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                text_format=ClientInfo  # Changed from response_format to text_format
            )
            
            # Get the parsed output
            extracted_info = response.output_parsed
            
            # Merge with existing info if provided
            if current_info:
                # Update only if new info is found
                if not extracted_info.name:
                    extracted_info.name = current_info.name
                if not extracted_info.last_name:
                    extracted_info.last_name = current_info.last_name
                if not extracted_info.ragione_sociale:
                    extracted_info.ragione_sociale = current_info.ragione_sociale
                if not extracted_info.email:
                    extracted_info.email = current_info.email
            
            logger.info(f"Extracted info - Complete: {extracted_info.found_all_info}")
            if extracted_info.what_is_missing:
                logger.info(f"Missing: {extracted_info.what_is_missing}")
            
            return extracted_info
            
        except Exception as e:
            logger.error(f"Error extracting client info: {e}")
            # Return existing info or empty if extraction fails
            return current_info or ClientInfo()
    
    def get_or_create_profile(self, whatsapp_number: str, conversation_id: str) -> ClientProfile:
        """
        Get existing profile or create new one for a WhatsApp user
        
        Args:
            whatsapp_number: User's WhatsApp number
            conversation_id: OpenAI conversation ID
            
        Returns:
            ClientProfile object
        """
        if whatsapp_number in self.profiles:
            profile = self.profiles[whatsapp_number]
            # Update conversation ID if different
            if profile.conversation_id != conversation_id:
                profile.conversation_id = conversation_id
                profile.updated_at = datetime.now()
            return profile
        
        # Create new profile
        profile = ClientProfile(
            info=ClientInfo(),
            whatsapp_number=whatsapp_number,
            conversation_id=conversation_id
        )
        self.profiles[whatsapp_number] = profile
        self.save_profiles()
        
        logger.info(f"Created new profile for {whatsapp_number}")
        return profile
    
    def update_profile(self, whatsapp_number: str, new_info: ClientInfo) -> ClientProfile:
        """
        Update a client's profile with new extracted information
        
        Args:
            whatsapp_number: User's WhatsApp number
            new_info: Updated ClientInfo
            
        Returns:
            Updated ClientProfile
        """
        if whatsapp_number not in self.profiles:
            logger.error(f"Profile not found for {whatsapp_number}")
            raise ValueError(f"Profile not found for {whatsapp_number}")
        
        profile = self.profiles[whatsapp_number]
        profile.info = new_info
        profile.updated_at = datetime.now()
        
        # Mark as complete if all info found
        if new_info.found_all_info and not profile.completed_at:
            profile.mark_complete()
            logger.info(f"Profile completed for {whatsapp_number}: {new_info.to_display_string()}")
        
        self.save_profiles()
        return profile
    
    def process_message(self, whatsapp_number: str, message: str, conversation_id: str) -> Tuple[ClientInfo, bool]:
        """
        Process a message and extract client information
        
        Args:
            whatsapp_number: User's WhatsApp number
            message: User's message
            conversation_id: OpenAI conversation ID
            
        Returns:
            Tuple of (ClientInfo, is_newly_complete)
        """
        # Get or create profile
        profile = self.get_or_create_profile(whatsapp_number, conversation_id)
        
        # Check if already complete
        was_complete = profile.info.found_all_info
        
        # Extract info from new message
        new_info = self.extract_client_info(message, profile.info)
        
        # Update profile
        updated_profile = self.update_profile(whatsapp_number, new_info)
        
        # Check if newly complete
        is_newly_complete = not was_complete and updated_profile.info.found_all_info
        
        return updated_profile.info, is_newly_complete
    
    def update_profile_manually(self, whatsapp_number: str, name: Optional[str] = None, 
                               last_name: Optional[str] = None, ragione_sociale: Optional[str] = None,
                               email: Optional[str] = None) -> bool:
        """
        Manually update a client's profile without extraction
        
        Args:
            whatsapp_number: User's WhatsApp number
            name: First name
            last_name: Last name
            ragione_sociale: Company name
            email: Email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if whatsapp_number not in self.profiles:
                logger.error(f"Profile not found for {whatsapp_number}")
                return False
            
            profile = self.profiles[whatsapp_number]
            
            # Update fields if provided
            if name is not None:
                profile.info.name = name if name.strip() else None
            if last_name is not None:
                profile.info.last_name = last_name if last_name.strip() else None
            if ragione_sociale is not None:
                profile.info.ragione_sociale = ragione_sociale if ragione_sociale.strip() else None
            if email is not None:
                profile.info.email = email if email.strip() else None
            
            # Recalculate completeness
            profile.info.found_all_info = all([
                profile.info.name,
                profile.info.last_name,
                profile.info.ragione_sociale,
                profile.info.email
            ])
            
            # Update what_is_missing
            missing = []
            if not profile.info.name:
                missing.append('nome')
            if not profile.info.last_name:
                missing.append('cognome')
            if not profile.info.ragione_sociale:
                missing.append('ragione sociale (azienda)')
            if not profile.info.email:
                missing.append('indirizzo email')
            
            if missing:
                if len(missing) == 1:
                    profile.info.what_is_missing = f"Manca ancora: {missing[0]}"
                else:
                    profile.info.what_is_missing = f"Mancano ancora: {', '.join(missing[:-1])} e {missing[-1]}"
            else:
                profile.info.what_is_missing = None
            
            # Update timestamps
            profile.updated_at = datetime.now()
            if profile.info.found_all_info and not profile.completed_at:
                profile.mark_complete()
                logger.info(f"Profile manually completed for {whatsapp_number}")
            
            self.save_profiles()
            logger.info(f"Profile manually updated for {whatsapp_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error in manual profile update: {e}")
            return False
    
    def get_profile_status(self, whatsapp_number: str) -> Optional[Dict]:
        """
        Get the current status of a user's profile
        
        Args:
            whatsapp_number: User's WhatsApp number
            
        Returns:
            Dictionary with profile status or None if not found
        """
        if whatsapp_number not in self.profiles:
            return None
        
        profile = self.profiles[whatsapp_number]
        return {
            "complete": profile.info.found_all_info,
            "display_name": profile.info.to_display_string(),
            "missing": profile.info.what_is_missing,
            "data": profile.info.dict(exclude={'found_all_info', 'what_is_missing'}),
            "created_at": profile.created_at.isoformat(),
            "completed_at": profile.completed_at.isoformat() if profile.completed_at else None
        }
    
    def format_extraction_summary(self, info: ClientInfo) -> str:
        """
        Format extraction results for logging/display
        
        Args:
            info: ClientInfo object
            
        Returns:
            Formatted string summary
        """
        parts = []
        if info.name:
            parts.append(f"Nome: {info.name}")
        if info.last_name:
            parts.append(f"Cognome: {info.last_name}")
        if info.ragione_sociale:
            parts.append(f"Azienda: {info.ragione_sociale}")
        if info.email:
            parts.append(f"Email: {info.email}")
        
        if parts:
            summary = " | ".join(parts)
            if info.found_all_info:
                summary = "✅ " + summary
            else:
                summary = "📝 " + summary
        else:
            summary = "❓ Nessuna informazione estratta"
        
        return summary