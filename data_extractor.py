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
from webhook_notifier import notify_profile_completion

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
        
        logger.info(f"Data Extractor initialized with model: {self.model}")
    
    def _calculate_what_is_missing(self, name, last_name, ragione_sociale, email):
        """Calculate what information is missing from a profile"""
        missing = []
        if not name:
            missing.append('nome')
        if not last_name:
            missing.append('cognome')
        if not ragione_sociale:
            missing.append('ragione sociale (azienda)')
        if not email:
            missing.append('indirizzo email')
        
        if missing:
            if len(missing) == 1:
                return f"Manca ancora: {missing[0]}"
            else:
                return f"Mancano ancora: {', '.join(missing[:-1])} e {missing[-1]}"
        return None
    
    def _create_client_info_from_db(self, profile_data: Dict) -> ClientInfo:
        """Create ClientInfo object from database data"""
        if not profile_data:
            return ClientInfo()
        
        # Convert empty strings to None for Pydantic validation
        def normalize_field(value):
            """Convert empty strings to None"""
            return value if value and value.strip() else None

        name = normalize_field(profile_data.get('name'))
        last_name = normalize_field(profile_data.get('last_name'))
        ragione_sociale = normalize_field(profile_data.get('ragione_sociale'))
        email = normalize_field(profile_data.get('email'))

        what_is_missing = self._calculate_what_is_missing(
            name, last_name, ragione_sociale, email
        )

        return ClientInfo(
            name=name,
            last_name=last_name,
            ragione_sociale=ragione_sociale,
            email=email,
            found_all_info=bool(profile_data.get('found_all_info', False)),
            what_is_missing=what_is_missing
        )
    
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
            
            # Log the FINAL merged state, not just extraction
            logger.info(f"Profile after extraction - Complete: {extracted_info.found_all_info}")
            if not extracted_info.found_all_info:
                logger.info(f"Still missing: {extracted_info.what_is_missing}")
            
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
        # Try to get from database
        profile_data = db.get_profile(whatsapp_number)
        
        if profile_data:
            # Create ClientProfile from database data
            client_info = self._create_client_info_from_db(profile_data)
            
            profile = ClientProfile(
                info=client_info,
                whatsapp_number=whatsapp_number,
                conversation_id=conversation_id,
                created_at=datetime.fromisoformat(profile_data['created_at']) if profile_data.get('created_at') else datetime.now(),
                updated_at=datetime.fromisoformat(profile_data['updated_at']) if profile_data.get('updated_at') else datetime.now(),
                completed_at=datetime.fromisoformat(profile_data['completed_at']) if profile_data.get('completed_at') else None,
                hubspot_synced=profile_data.get('hubspot_synced', False),
                hubspot_contact_id=profile_data.get('hubspot_contact_id')
            )
            
            # Update conversation ID if different
            if profile_data.get('conversation_id') != conversation_id:
                db.save_profile(whatsapp_number, {'conversation_id': conversation_id})
            
            return profile
        
        # Create new profile
        profile = ClientProfile(
            info=ClientInfo(),
            whatsapp_number=whatsapp_number,
            conversation_id=conversation_id
        )
        
        # Save new profile to database
        profile_data = {
            'name': None,
            'last_name': None,
            'ragione_sociale': None,
            'email': None,
            'conversation_id': conversation_id,
            'hubspot_synced': False,
            'hubspot_contact_id': None
        }
        db.save_profile(whatsapp_number, profile_data)
        
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
        # Get existing profile from database
        existing_data = db.get_profile(whatsapp_number)
        if not existing_data:
            logger.error(f"Profile not found for {whatsapp_number}")
            raise ValueError(f"Profile not found for {whatsapp_number}")
        
        # Check if newly complete
        was_complete = bool(existing_data.get('found_all_info', False))
        is_newly_complete = not was_complete and new_info.found_all_info
        
        # Save to database
        profile_data = {
            'name': new_info.name,
            'last_name': new_info.last_name,
            'ragione_sociale': new_info.ragione_sociale,
            'email': new_info.email,
            'conversation_id': existing_data.get('conversation_id'),
            'hubspot_synced': existing_data.get('hubspot_synced', False),
            'hubspot_contact_id': existing_data.get('hubspot_contact_id')
        }
        db.save_profile(whatsapp_number, profile_data)
        
        if is_newly_complete:
            logger.info(f"Profile completed for {whatsapp_number}: {new_info.to_display_string()}")
            
            # Send webhook notification asynchronously
            try:
                # Get the complete profile data for webhook
                profile_for_webhook = db.get_profile(whatsapp_number)
                if profile_for_webhook:
                    notify_profile_completion(whatsapp_number, profile_for_webhook)
            except Exception as e:
                logger.error(f"Failed to send webhook notification: {e}")
                # Don't let webhook failure affect normal flow
        
        logger.debug(f"Profile saved to database for {whatsapp_number}")
        
        # Create and return ClientProfile object
        profile = ClientProfile(
            info=new_info,
            whatsapp_number=whatsapp_number,
            conversation_id=existing_data.get('conversation_id', ''),
            created_at=datetime.fromisoformat(existing_data['created_at']) if existing_data.get('created_at') else datetime.now(),
            updated_at=datetime.now(),
            completed_at=datetime.now() if is_newly_complete else (datetime.fromisoformat(existing_data['completed_at']) if existing_data.get('completed_at') else None),
            hubspot_synced=existing_data.get('hubspot_synced', False),
            hubspot_contact_id=existing_data.get('hubspot_contact_id')
        )
        
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
            # Get existing profile from database or create new
            existing_data = db.get_profile(whatsapp_number)
            
            # Prepare updated data
            if existing_data:
                # Start with existing data
                updated_data = {
                    'name': existing_data.get('name'),
                    'last_name': existing_data.get('last_name'),
                    'ragione_sociale': existing_data.get('ragione_sociale'),
                    'email': existing_data.get('email'),
                    'conversation_id': existing_data.get('conversation_id'),
                    'hubspot_synced': existing_data.get('hubspot_synced', False),
                    'hubspot_contact_id': existing_data.get('hubspot_contact_id')
                }
            else:
                # Create new profile data
                updated_data = {
                    'name': None,
                    'last_name': None,
                    'ragione_sociale': None,
                    'email': None,
                    'conversation_id': '',
                    'hubspot_synced': False,
                    'hubspot_contact_id': None
                }
            
            # Update fields if provided
            if name is not None:
                updated_data['name'] = name.strip() if name.strip() else None
            if last_name is not None:
                updated_data['last_name'] = last_name.strip() if last_name.strip() else None
            if ragione_sociale is not None:
                updated_data['ragione_sociale'] = ragione_sociale.strip() if ragione_sociale.strip() else None
            if email is not None:
                updated_data['email'] = email.strip() if email.strip() else None
            
            # Save to database (database will handle found_all_info flag)
            db.save_profile(whatsapp_number, updated_data)
            
            # Check if profile is now complete
            is_complete = all([
                updated_data['name'],
                updated_data['last_name'],
                updated_data['ragione_sociale'],
                updated_data['email']
            ])
            
            if is_complete:
                logger.info(f"Profile manually completed for {whatsapp_number}")
            
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
        # Get from database
        profile_data = db.get_profile(whatsapp_number)
        if not profile_data:
            return None
        
        # Create ClientInfo to get display string and missing info
        client_info = self._create_client_info_from_db(profile_data)
        
        return {
            "complete": bool(profile_data.get('found_all_info', False)),
            "display_name": client_info.to_display_string(),
            "missing": client_info.what_is_missing,
            "data": {
                'name': profile_data.get('name'),
                'last_name': profile_data.get('last_name'),
                'ragione_sociale': profile_data.get('ragione_sociale'),
                'email': profile_data.get('email')
            },
            "created_at": profile_data.get('created_at'),
            "completed_at": profile_data.get('completed_at')
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