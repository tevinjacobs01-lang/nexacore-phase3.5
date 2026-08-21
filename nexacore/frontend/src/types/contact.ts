export interface Contact {
  id: string;
  name: string | null;
  phone: string | null;
  email: string | null;
  preferred_contact_method: string | null;
  contact_type: string | null;
  source: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export const CONTACT_TYPES = ["property_owner", "buyer", "tenant", "landlord", "seller", "agent", "other"];
export const PREFERRED_CONTACT_METHODS = ["phone", "email", "sms", "whatsapp", "any"];
