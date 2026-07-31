import axios from "axios";

const API_BASE = "http://localhost:8000";

export interface ItineraryItem {
  time: string;
  spot: string;
  category: string;
  duration: string;
  cost: number;
  lat: number;
  lng: number;
  note: string;
}

export interface DayPlan {
  day: number;
  items: ItineraryItem[];
  transport: string;
  day_cost: number;
}

export interface Itinerary {
  destination: string;
  days: number;
  itinerary: DayPlan[];
  total_cost: number;
  summary: string;
}

export interface Verification {
  spots_valid: boolean;
  spots_total?: number;
  spots_verified?: number;
  budget_valid: boolean;
  budget_total?: number;
  budget_limit?: number;
  budget_utilization?: number;
  route_valid: boolean;
}

export interface GenerateResponse {
  itinerary: Itinerary;
  verification: Verification;
}

export interface GenerateRequest {
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
}

export async function generateItinerary(req: GenerateRequest): Promise<GenerateResponse> {
  const { data } = await axios.post<GenerateResponse>(`${API_BASE}/api/generate`, req);
  return data;
}

export async function submitFeedback(payload: {
  destination: string;
  days: number;
  budget: number;
  preferences: string[];
  feedback_type: string;
  comment?: string;
}): Promise<{ status: string; id: number }> {
  const { data } = await axios.post(`${API_BASE}/api/feedback`, payload);
  return data;
}

export async function chatWithPet(message: string, destination?: string): Promise<{ reply: string }> {
  const { data } = await axios.post(`${API_BASE}/api/chat`, { message, destination });
  return data;
}

export async function chatWithPetStream(
  message: string,
  destination: string | undefined,
  onThinking: (text: string) => void,
  onContent: (chunk: string) => void,
  onDone: () => void,
): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, destination }),
  });

  const reader = resp.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.type === "thinking") onThinking(data.content);
        else if (data.type === "content") onContent(data.content);
        else if (data.type === "done") onDone();
      } catch { /* skip */ }
    }
  }
  onDone();
}