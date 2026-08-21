export interface Lead {
  id: string;
  property_id: string;
  contact_id: string | null;
  status: string;
  priority: "low" | "medium" | "high";
  assigned_agent_id: string | null;
  last_contacted_at: string | null;
  next_follow_up: string | null;
  notes: string | null;
  created_at: string;
}

export const PIPELINE_STAGES = [
  { key: "new", label: "New" },
  { key: "researching", label: "Researching" },
  { key: "contacted", label: "Contacted" },
  { key: "responded", label: "Responded" },
  { key: "qualified", label: "Qualified" },
  { key: "follow_up", label: "Follow-up" },
  { key: "appointment", label: "Appointment" },
  { key: "listing_opportunity", label: "Listing Opportunity" },
  { key: "mandate_agreement", label: "Mandate/Agreement" },
  { key: "won", label: "Won" },
  { key: "lost", label: "Lost" },
];
