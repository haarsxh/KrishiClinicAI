export interface Prediction {
  id: string;
  crop_type: string;
  image_filename: string | null;
  farmer_notes: string | null;
  predicted_disease: string;
  confidence: number;
  severity: string | null;
  recommendation: string | null;
  possible_reasons?: string | null;
  location?: string | null;
  language?: string | null;
  status?: string;
  ai_provider: string;
  created_at: string;

  farmer_id?: string | null;
  after_image_filename?: string | null;
  after_notes?: string | null;
  after_uploaded_at?: string | null;
}

export interface PredictionListItem {
  id: string;
  crop_type: string;
  image_filename: string | null;
  farmer_notes: string | null;
  predicted_disease: string;
  confidence: number;
  severity: string | null;
  recommendation: string | null;
  possible_reasons: string | null;
  status?: string;
  ai_provider: string;
  created_at: string;
  location: string | null;
}

export interface PredictionListResponse {
  items: PredictionListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface DiseaseCount {
  disease: string;
  count: number;
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface AnalyticsSummary {
  total_predictions: number;
  average_confidence: number;
  disease_distribution: DiseaseCount[];
  daily_volume: DailyCount[];
  severity_distribution: Record<string, number>;
  top_crop: string | null;
}

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
}

export const CROP_TYPES = [
  "Wheat",
  "Rice",
  "Tomato",
  "Corn",
  "Potato",
  "Cotton",
  "Sugarcane",
  "Soybean",
  "Mustard",
  "Groundnut",
  "Chilli",
] as const;

export type CropType = (typeof CROP_TYPES)[number];

export const AI_PROVIDERS = [
  { value: "", label: "Default (server config)" },
  { value: "gemini", label: " Google Gemini" },
  { value: "groq", label: " Groq (Llama 4)" },
  { value: "local", label: " Local PyTorch (EfficientNetV2)" },
  { value: "mock", label: " Mock (deterministic)" },
] as const;

// ─── Auth ───────────────────────────────────────────

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterPayload extends LoginCredentials {
  role: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface UserAccount {
  id: string;
  username: string;
  role: string;
  created_at?: string;
}

// ─── Outbreak surveillance ──────────────────────────

export interface OutbreakCluster {
  id: string;
  region: string;
  district: string;
  crop: string;
  disease: string;
  threat_level: string;
  active_cases: number;
  trend: string;
  radius_km: number;
  latitude: number;
  longitude: number;
  prevention_advisory: string;
  last_reported: string;
}

export interface OutbreakSummary {
  total_active_clusters: number;
  high_risk_alerts: number;
  monitored_regions: number;
  clusters: OutbreakCluster[];
}

// ─── Medicine advisor ───────────────────────────────

export interface TreatmentDetail {
  chemical: string;
  fungicide: string;
  organic: string;
  dose: string;
  frequency: string;
  notes: string;
}

export interface AllStagesTreatment {
  sowing?: TreatmentDetail | null;
  mid_season?: TreatmentDetail | null;
  pre_harvest?: TreatmentDetail | null;
}

export interface MedicineTreatment {
  crop: string;
  disease: string;
  stage?: string | null;
  treatment?: TreatmentDetail | null;
  all_stages?: AllStagesTreatment | null;
}
