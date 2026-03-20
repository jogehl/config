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

export class ConfigBuilderApiClient {
  constructor(private readonly baseUrl = "http://localhost:8000/api/v1") {}

  async getFormats(): Promise<ConfigFormat[]> {
    const response = await fetch(`${this.baseUrl}/formats`);
    const body = await response.json();
    return body.formats;
  }

  async getClasses(): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/get-config-classes`);
    const body = await response.json();
    return body.classes;
  }

  async getClassSchema(className: string): Promise<ClassSchemaResponse> {
    const response = await fetch(
      `${this.baseUrl}/get-config-class/${encodeURIComponent(className)}`
    );
    return response.json();
  }

  async loadConfig(payload: LoadConfigRequest): Promise<LoadConfigResponse> {
    const response = await fetch(`${this.baseUrl}/load-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return response.json();
  }

  async configMetadata(
    payload: ConfigMetadataRequest
  ): Promise<ConfigMetadataResponse> {
    const response = await fetch(`${this.baseUrl}/config-metadata`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return response.json();
  }

  async validateConfig(payload: ValidateConfigRequest): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}/validate-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return response.json();
  }

  async saveConfig(payload: SaveConfigRequest): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}/save-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return response.json();
  }
}
