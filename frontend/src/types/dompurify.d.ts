declare module 'dompurify' {
  export interface DOMPurifyConfig {
    ALLOWED_TAGS?: string[];
    ALLOWED_ATTR?: string[];
    ALLOW_DATA_ATTR?: boolean;
    ALLOW_UNKNOWN_PROTOCOLS?: boolean;
    SAFE_FOR_TEMPLATES?: boolean;
    WHOLE_DOCUMENT?: boolean;
    RETURN_DOM?: boolean;
    RETURN_DOM_FRAGMENT?: boolean;
    RETURN_DOM_IMPORT?: boolean;
    RETURN_TRUSTED_TYPE?: boolean;
    FORCE_BODY?: boolean;
    SANITIZE_DOM?: boolean;
    KEEP_CONTENT?: boolean;
    IN_PLACE?: boolean;
    USE_PROFILES?: { [key: string]: any };
    FORBID_TAGS?: string[];
    FORBID_ATTR?: string[];
    FORBID_CONTENTS?: string[];
    [key: string]: any;
  }

  export interface DOMPurifyInstance {
    sanitize(dirty: string | Node, config?: DOMPurifyConfig): string;
    sanitize(dirty: string | Node, config: DOMPurifyConfig & { RETURN_DOM_FRAGMENT?: false; RETURN_DOM?: true }): HTMLElement;
    sanitize(dirty: string | Node, config: DOMPurifyConfig & { RETURN_DOM_FRAGMENT: true; RETURN_DOM?: false }): DocumentFragment;
    addHook(hook: string, cb: (currentNode: any, data: any, config: any) => void): void;
    removeHook(hook: string): void;
    removeHooks(hooks: string): void;
    removeAllHooks(): void;
    setConfig(config: DOMPurifyConfig): void;
    clearConfig(): void;
    isValidAttribute(tag: string, attr: string, value: string): boolean;
  }

  const DOMPurify: DOMPurifyInstance;
  export default DOMPurify;
}
