export interface Interaction {
  id: string;
  contact_id: string | null;
  lead_id: string | null;
  user_id: string | null;
  interaction_type: string;
  direction: string;
  outcome: string | null;
  notes: string | null;
  occurred_at: string;
}

export interface Note {
  id: string;
  entity_type: string;
  entity_id: string;
  content: string;
  is_private: boolean;
  author_id: string | null;
  created_at: string;
}

export interface TaskItem {
  id: string;
  title: string;
  description: string | null;
  assigned_user_id: string | null;
  lead_id: string | null;
  contact_id: string | null;
  due_date: string | null;
  priority: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface FollowUp {
  id: string;
  lead_id: string | null;
  contact_id: string | null;
  follow_up_type: string;
  due_at: string;
  status: string;
  notes: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Appointment {
  id: string;
  lead_id: string | null;
  contact_id: string | null;
  starts_at: string;
  duration_minutes: number;
  location: string | null;
  appointment_type: string;
  notes: string | null;
  status: string;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  template_type: string;
  subject: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export const INTERACTION_TYPES = ["call", "email", "meeting", "message", "note", "status_change"];
export const INTERACTION_DIRECTIONS = ["outgoing", "incoming", "internal"];
export const TASK_PRIORITIES = ["low", "medium", "high", "urgent"];
export const TASK_STATUSES = ["pending", "in_progress", "completed", "cancelled"];
export const FOLLOW_UP_TYPES = ["call", "message", "email", "meeting", "general"];
export const APPOINTMENT_TYPES = ["viewing", "listing_presentation", "signing", "consultation", "other"];
export const APPOINTMENT_STATUSES = ["scheduled", "confirmed", "completed", "cancelled", "no_show", "rescheduled"];
export const TEMPLATE_TYPES = [
  "initial_seller_contact", "follow_up", "appointment_confirmation",
  "appointment_reminder", "buyer_enquiry", "rental_enquiry", "general_response",
];
