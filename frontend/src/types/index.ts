import type { components, paths } from './api';

export type { paths, components };

export type ApiSchema<T extends keyof components['schemas']> = components['schemas'][T];

// Atajos de tipos derivados del contrato OpenAPI
export type ApiBook = components['schemas']['Book'];
export type ApiUserBasic = components['schemas']['UserBasic'];
export type ApiActivity = components['schemas']['Activity'];
export type ApiReadingList = components['schemas']['ReadingList'];
