"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { settingsApi } from "@/lib/api/settings";
import { ProviderType } from "@/lib/types";
import type {
  EmbeddingProviderResponse,
  EmbeddingProviderUpdate,
} from "@/lib/types";

export function EmbeddingProviderSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const [provider, setProvider] = useState<ProviderType>(ProviderType.OPENAI);
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("http://localhost:11434");
  const [currentSettings, setCurrentSettings] =
    useState<EmbeddingProviderResponse | null>(null);

  // Load current settings
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const settings = await settingsApi.getEmbeddingProvider();
      setCurrentSettings(settings);
      setProvider(settings.provider);
      setModel(settings.model);
      if (settings.base_url) {
        setBaseUrl(settings.base_url);
      }
      // Don't load API key for security
    } catch (error) {
      console.error("Failed to load settings:", error);
      toast.error("Failed to load embedding provider settings");
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      setTestResult(null);

      const testData = {
        provider,
        model,
        api_key: (provider === ProviderType.OPENAI || provider === ProviderType.GEMINI || provider === ProviderType.CLAUDE) ? apiKey || undefined : undefined,
        base_url: provider === ProviderType.OLLAMA ? baseUrl : undefined,
      };

      const result = await settingsApi.testEmbeddingProvider(testData);
      setTestResult(result);

      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      console.error("Connection test failed:", error);
      toast.error("Connection test failed");
      setTestResult({
        success: false,
        message: "Connection test failed",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);

      const updateData: EmbeddingProviderUpdate = {
        provider,
        model,
      };

      if ((provider === ProviderType.OPENAI || provider === ProviderType.GEMINI || provider === ProviderType.CLAUDE) && apiKey) {
        updateData.api_key = apiKey;
      }

      if (provider === ProviderType.OLLAMA) {
        updateData.base_url = baseUrl;
      }

      const result = await settingsApi.updateEmbeddingProvider(updateData);
      setCurrentSettings(result);

      toast.success("Embedding provider settings saved successfully");

      // Clear API key input after saving
      setApiKey("");
    } catch (error: any) {
      console.error("Failed to save settings:", error);
      toast.error(
        error.response?.data?.detail || "Failed to save embedding provider settings"
      );
    } finally {
      setSaving(false);
    }
  };

  // Model options per provider
  const getModelOptions = () => {
    switch (provider) {
      case ProviderType.OPENAI:
        return [
          { value: "text-embedding-3-small", label: "text-embedding-3-small (1536 dims)" },
          { value: "text-embedding-3-large", label: "text-embedding-3-large (3072 dims)" },
          { value: "text-embedding-ada-002", label: "text-embedding-ada-002 (1536 dims, legacy)" },
        ];
      case ProviderType.OLLAMA:
        return [
          { value: "nomic-embed-text", label: "nomic-embed-text (768 dims)" },
          { value: "mxbai-embed-large", label: "mxbai-embed-large (1024 dims)" },
          { value: "all-minilm", label: "all-minilm (384 dims)" },
        ];
      case ProviderType.GEMINI:
        return [
          { value: "text-embedding-004", label: "text-embedding-004 (768 dims)" },
          { value: "embedding-001", label: "embedding-001 (768 dims)" },
        ];
      case ProviderType.CLAUDE:
        return [
          { value: "voyage-2", label: "voyage-2 (1024 dims)" },
          { value: "voyage-large-2", label: "voyage-large-2 (1536 dims)" },
          { value: "voyage-code-2", label: "voyage-code-2 (1536 dims)" },
          { value: "voyage-lite-02-instruct", label: "voyage-lite-02-instruct (1024 dims)" },
        ];
      default:
        return [];
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-10">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Embedding Provider</CardTitle>
        <CardDescription>
          Configure which AI provider to use for document embeddings. This affects how your
          documents are processed and searched.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Provider Selection */}
        <div className="space-y-2">
          <Label htmlFor="provider">Provider</Label>
          <Select
            value={provider}
            onValueChange={(value) => {
              setProvider(value as ProviderType);
              setTestResult(null);
            }}
          >
            <SelectTrigger id="provider">
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ProviderType.OPENAI}>OpenAI</SelectItem>
              <SelectItem value={ProviderType.OLLAMA}>Ollama (Local)</SelectItem>
              <SelectItem value={ProviderType.GEMINI}>Google Gemini</SelectItem>
              <SelectItem value={ProviderType.CLAUDE}>Claude (Voyage AI)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Model Selection */}
        <div className="space-y-2">
          <Label htmlFor="model">Model</Label>
          <Select
            value={model}
            onValueChange={(value) => {
              setModel(value);
              setTestResult(null);
            }}
          >
            <SelectTrigger id="model">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {getModelOptions().map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-sm text-muted-foreground">
            Current: {currentSettings?.model || "Not set"} ({currentSettings?.dimensions || 0} dimensions)
          </p>
        </div>

        {/* API Key (for OpenAI) */}
        {provider === ProviderType.OPENAI && (
          <div className="space-y-2">
            <Label htmlFor="api_key">
              API Key {currentSettings?.has_api_key && "(configured)"}
            </Label>
            <Input
              id="api_key"
              type="password"
              placeholder={
                currentSettings?.has_api_key
                  ? "Leave blank to keep existing key"
                  : "sk-..."
              }
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setTestResult(null);
              }}
            />
            <p className="text-sm text-muted-foreground">
              Your API key is stored securely in Vault. Get your key from{" "}
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                OpenAI Platform
              </a>
            </p>
          </div>
        )}

        {/* API Key (for Gemini) */}
        {provider === ProviderType.GEMINI && (
          <div className="space-y-2">
            <Label htmlFor="api_key">
              API Key {currentSettings?.has_api_key && "(configured)"}
            </Label>
            <Input
              id="api_key"
              type="password"
              placeholder={
                currentSettings?.has_api_key
                  ? "Leave blank to keep existing key"
                  : "AIza..."
              }
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setTestResult(null);
              }}
            />
            <p className="text-sm text-muted-foreground">
              Your API key is stored securely in Vault. Get your key from{" "}
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                Google AI Studio
              </a>
            </p>
          </div>
        )}

        {/* API Key (for Claude/Voyage AI) */}
        {provider === ProviderType.CLAUDE && (
          <div className="space-y-2">
            <Label htmlFor="api_key">
              Voyage AI API Key {currentSettings?.has_api_key && "(configured)"}
            </Label>
            <Input
              id="api_key"
              type="password"
              placeholder={
                currentSettings?.has_api_key
                  ? "Leave blank to keep existing key"
                  : "pa-..."
              }
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setTestResult(null);
              }}
            />
            <p className="text-sm text-muted-foreground">
              Your API key is stored securely in Vault. Get your key from{" "}
              <a
                href="https://www.voyageai.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                Voyage AI
              </a>
              {" "}(Anthropic&apos;s recommended embeddings partner)
            </p>
          </div>
        )}

        {/* Base URL (for Ollama) */}
        {provider === ProviderType.OLLAMA && (
          <div className="space-y-2">
            <Label htmlFor="base_url">Ollama URL</Label>
            <Input
              id="base_url"
              type="text"
              placeholder="http://localhost:11434"
              value={baseUrl}
              onChange={(e) => {
                setBaseUrl(e.target.value);
                setTestResult(null);
              }}
            />
            <p className="text-sm text-muted-foreground">
              Make sure Ollama is running locally. You can start it with{" "}
              <code className="rounded bg-muted px-1 py-0.5">ollama serve</code>
            </p>
          </div>
        )}

        {/* Test Connection Result */}
        {testResult && (
          <div
            className={`flex items-center gap-2 rounded-md border p-3 ${
              testResult.success
                ? "bg-success-light text-success-light-foreground border-success-light-foreground/20"
                : "bg-status-failed text-status-failed-foreground border-status-failed-foreground/20"
            }`}
          >
            {testResult.success ? (
              <CheckCircle2 className="h-5 w-5" />
            ) : (
              <XCircle className="h-5 w-5" />
            )}
            <p className="text-sm">{testResult.message}</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button
            onClick={handleTestConnection}
            disabled={testing || !model}
            variant="outline"
          >
            {testing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Test Connection
          </Button>

          <Button onClick={handleSave} disabled={saving || !model}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Settings
          </Button>
        </div>

        {/* Warning */}
        <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-900">
          <strong>Note:</strong> After changing providers, you may want to reprocess existing
          documents to use the new embedding model. You can do this from the Documents page.
        </div>
      </CardContent>
    </Card>
  );
}
