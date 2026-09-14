/** Framework-independent extension contract. Never pass provider/admin tokens. */
export type Theme = 'light' | 'dark';
export type Unsubscribe = () => void;
export interface ModuleContext {
  readonly moduleId: string;
  readonly organizationId: string;
  readonly routeBase: string;
  readonly locale: string;
  readonly theme: Theme;
  readonly tokens: Readonly<Record<string, string>>;
  readonly signal: AbortSignal;
  navigate(path: string): void;
  reportError(error: Error): void;
}
export interface MountedModule {
  updateContext(context: ModuleContext): void | Promise<void>;
  canLeave(): boolean | Promise<boolean>;
  unmount(): void | Promise<void>;
}
export interface WebModule {
  mount(container: HTMLElement, context: ModuleContext): MountedModule | Promise<MountedModule>;
}
export type ModuleLoader = () => Promise<WebModule>;

export function assertModulePath(base: string, path: string): string {
  let decoded = path;
  for (let i = 0; i < 3; i++) decoded = decodeURIComponent(decoded);
  if (!base.startsWith('/_platform/apps/') || base.endsWith('/') || base.includes('..')) throw new Error('Invalid module base');
  if (!decoded.startsWith('/') || decoded.startsWith('//') || /[\\\u0000-\u001f]/.test(decoded)) throw new Error('Unsafe module path');
  const pathname = decoded.split(/[?#]/, 1)[0];
  if (pathname.split('/').some(p => p === '.' || p === '..')) throw new Error('Path traversal');
  if (pathname !== base && !pathname.startsWith(base + '/')) throw new Error('Outside module namespace');
  return path;
}

/** Stale async mounts get a detached container and are disposed, not shown. */
export class ModuleController {
  private epoch = 0;
  private current: MountedModule | null = null;
  private slot: HTMLElement | null = null;
  private abort: AbortController | null = null;
  private organizationId: string | null = null;

  async open(loader: ModuleLoader, container: HTMLElement, input: Omit<ModuleContext, 'signal'>): Promise<boolean> {
    if (this.current && !(await this.current.canLeave())) return false;
    await this.dispose();
    const epoch = ++this.epoch;
    const abort = new AbortController();
    this.abort = abort;
    const slot = container.ownerDocument.createElement('div');
    slot.dataset.moduleId = input.moduleId;
    this.slot = slot;
    container.replaceChildren(slot);
    const context: ModuleContext = {
      ...input, signal: abort.signal,
      navigate: path => input.navigate(assertModulePath(input.routeBase, path)),
    };
    try {
      const module = await loader();
      if (epoch !== this.epoch || abort.signal.aborted) return false;
      const instance = await module.mount(slot, context);
      if (epoch !== this.epoch || abort.signal.aborted) {
        await instance.unmount(); slot.remove(); return false;
      }
      this.current = instance;
      this.organizationId = input.organizationId;
      return true;
    } catch (error) {
      slot.remove();
      abort.abort();
      if (epoch === this.epoch) {
        this.slot = null; this.abort = null;
        input.reportError(error instanceof Error ? error : new Error(String(error)));
      }
      return false;
    }
  }

  async update(context: Omit<ModuleContext, 'signal'>): Promise<void> {
    if (!this.current || !this.abort) return;
    if (context.organizationId !== this.organizationId) throw new Error('Organization switch requires unmount');
    await this.current.updateContext({...context, signal: this.abort.signal,
      navigate: path => context.navigate(assertModulePath(context.routeBase, path))});
  }

  async canLeave(): Promise<boolean> { return this.current ? this.current.canLeave() : true; }

  async dispose(): Promise<void> {
    ++this.epoch;
    this.abort?.abort();
    const current = this.current; const slot = this.slot;
    this.current = null; this.slot = null; this.abort = null; this.organizationId = null;
    try { if (current) await current.unmount(); }
    finally { slot?.remove(); }
  }
}
