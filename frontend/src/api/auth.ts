import { getAccessToken, setAccessToken } from "./auth-storage";


type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};


export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error(`Login failed with HTTP ${response.status}`);
  }

  const data = (await response.json()) as LoginResponse;
  setAccessToken(data.access_token);
  return data;
}


export function requireAccessToken(): string {
  const token = getAccessToken();
  if (!token) {
    throw new Error("Not authenticated.");
  }
  return token;
}
