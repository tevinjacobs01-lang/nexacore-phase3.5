export interface LeadScoreRule {
  id: string;
  name: string;
  rule_key: string;
  points: number;
  is_active: boolean;
  config: string | null;
  updated_at: string;
}
