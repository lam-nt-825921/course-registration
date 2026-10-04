export interface User {
  id: string;
  email: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  token: any;
  accessToken: string;
  user: User;
}
