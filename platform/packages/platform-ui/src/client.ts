export interface PlatformSession {
  user: {id: string; name: string; email: string};
  organization: {id: string; name: string; origin: string};
  role: string;
  permissions: string[];
  modules: {id: string; title: string; route: string; permission: string}[];
  csrf_token: string;
  production_ready: false;
}
export interface Meter { id: string; label: string; serial: string; unit: string; location: string; }
export interface Reading { id: string; value: string; measured_at: string; kind: string; author_id: string; }
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
const prefix = '/_platform/api';
export class PlatformClient {
  private csrf = '';
  async session(): Promise<PlatformSession> {
    const session = await this.request<PlatformSession>('/me');
    this.csrf = session.csrf_token;
    return session;
  }
  async request<T>(path: string, method = 'GET', body?: unknown, key?: string): Promise<T> {
    if (!path.startsWith('/') || path.startsWith('//') || /[\\%]/.test(path) || path.includes('..')) throw new Error('Invalid API path');
    if (!['GET','POST','PUT','DELETE'].includes(method)) throw new Error('Unsupported API method');
    const headers: Record<string, string> = {'Accept': 'application/json'};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (method !== 'GET') headers['X-CSRF-Token'] = this.csrf;
    if (key) headers['Idempotency-Key'] = key;
    const response = await fetch(prefix + path, {method, credentials: 'same-origin', cache: 'no-store',
      headers, body: body === undefined ? undefined : JSON.stringify(body)});
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(response.status,
      typeof data?.detail === 'string' ? data.detail : `Ошибка запроса (${response.status})`);
    return data as T;
  }
}
