import type { ClassSchemaResponse, JsonValue } from "./types";

export type ConfigFormat = "json" | "yaml" | "toml";

export interface LoadConfigRequest {
  config_path: string;
  autoreload?: boolean;
}

export interface ValidateConfigRequest {
  class_name: string;
  data: Record<string, JsonValue>;
}

export interface SaveConfigRequest {
  config_path: string;
  config_type: ConfigFormat;
  data: Record<string, JsonValue> | JsonValue[];
}

export interface ConfigMetadataRequest {
  config_path: string;
}

export interface ConfigMetadataResponse {
  exists: boolean;
  mtime_ns: number | null;
  sha256: string | null;
}

export interface LoadConfigResponse {
  config: JsonValue;
  metadata: ConfigMetadataResponse;
}

export interface BrowseEntry {
  name: string;
  type: "file" | "directory";
}

export interface BrowseResponse {
  path: string;
  parent: string | null;
  entries: BrowseEntry[];
}

export class ConfigBuilderApiClient {
  constructor(private readonly baseUrl = "http://localhost:8000/api/v1") {}

  private async request<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, init);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail =
        (body as { detail?: string }).detail ?? response.statusText;
      throw new Error(detail);
    }
    return response.json() as Promise<T>;
  }

  async getFormats(): Promise<ConfigFormat[]> {
    const body = await this.request<{ formats: ConfigFormat[] }>(
      `${this.baseUrl}/formats`,
    );
    return body.formats;
  }

  async getClasses(): Promise<string[]> {
    const body = await this.request<{ classes: string[] }>(
      `${this.baseUrl}/get-config-classes`,
    );
    return body.classes;
  }

  async getClassSchema(className: string): Promise<ClassSchemaResponse> {
    return this.request<ClassSchemaResponse>(
      `${this.baseUrl}/get-config-class/${encodeURIComponent(className)}`,
    );
  }

  async loadConfig(payload: LoadConfigRequest): Promise<LoadConfigResponse> {
    return this.request<LoadConfigResponse>(`${this.baseUrl}/load-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async configMetadata(
    payload: ConfigMetadataRequest,
  ): Promise<ConfigMetadataResponse> {
    return this.request<ConfigMetadataResponse>(
      `${this.baseUrl}/config-metadata`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
  }

  async validateConfig(payload: ValidateConfigRequest): Promise<unknown> {
    return this.request(`${this.baseUrl}/validate-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async browse(directory = "."): Promise<BrowseResponse> {
    return this.request<BrowseResponse>(
      `${this.baseUrl}/browse?directory=${encodeURIComponent(directory)}`,
    );
  }

  async saveConfig(payload: SaveConfigRequest): Promise<unknown> {
    return this.request(`${this.baseUrl}/save-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
}
