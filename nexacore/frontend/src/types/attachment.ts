export interface Attachment {
  id: string;
  entity_type: string;
  entity_id: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  uploaded_by: string | null;
  created_at: string;
}
