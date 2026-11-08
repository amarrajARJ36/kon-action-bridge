import { NextResponse } from "next/server";
import { neon } from "@neondatabase/serverless";

export const dynamic = "force-dynamic";

export async function GET() {
  const results: Record<string, any> = {
    timestamp: new Date().toISOString(),
    services: {},
  };

  // 1. Test Neon Postgres
  try {
    const dbUrl = process.env.DATABASE_URL || process.env.DATABASE_URL_UNPOOLED;
    if (!dbUrl) {
      throw new Error("DATABASE_URL not configured");
    }
    const sql = neon(dbUrl);
    const dbRes = await sql`SELECT version(), current_database(), (SELECT count(*) FROM products) as products_count;`;
    results.services.postgres = {
      status: "connected",
      driver: "@neondatabase/serverless",
      database: dbRes[0]?.current_database || "neondb",
      version: dbRes[0]?.version || "PostgreSQL 18.6",
      productsCount: Number(dbRes[0]?.products_count || 0),
    };
  } catch (err: any) {
    results.services.postgres = {
      status: "error",
      error: err.message,
    };
  }

  // 2. Test Neon Functions
  try {
    const functionUrl =
      process.env.NEXT_PUBLIC_NEON_FUNCTION_URL ||
      "https://br-patient-union-bdtf9eqy-hello.compute.c-8.us-east-2.aws.neon.tech/";
    const fnRes = await fetch(functionUrl, { cache: "no-store" });
    const fnText = await fnRes.text();
    results.services.functions = {
      status: fnRes.ok ? "connected" : "error",
      statusCode: fnRes.status,
      url: functionUrl,
      output: fnText.trim(),
    };
  } catch (err: any) {
    results.services.functions = {
      status: "error",
      error: err.message,
    };
  }

  // 3. Test Neon AI Gateway
  try {
    const gatewayBaseUrl = process.env.NEON_AI_GATEWAY_BASE_URL;
    const gatewayToken = process.env.NEON_AI_GATEWAY_TOKEN;
    if (gatewayBaseUrl && gatewayToken) {
      const gwRes = await fetch(`${gatewayBaseUrl}/v1/models`, {
        headers: {
          Authorization: `Bearer ${gatewayToken}`,
        },
        cache: "no-store",
      });
      const gwData = await gwRes.json();
      results.services.aiGateway = {
        status: gwRes.ok ? "connected" : "error",
        statusCode: gwRes.status,
        baseUrl: gatewayBaseUrl,
        catalogCount: gwData?.data?.length || 0,
        availability: gwData?.request_context_availability?.http?.status || "active",
        notice:
          gwData?.request_context_availability?.http?.reason === "paid_plan_required"
            ? "AI Gateway provisioned & active. Prepaid AI credits required to route requests; direct Gemini provider active as primary zero-cost engine."
            : "AI Gateway fully active.",
      };
    } else {
      results.services.aiGateway = {
        status: "not_configured",
      };
    }
  } catch (err: any) {
    results.services.aiGateway = {
      status: "error",
      error: err.message,
    };
  }

  // 4. Test Neon Realtime
  results.services.realtime = {
    status: process.env.NEON_REALTIME_URL ? "configured" : "not_configured",
    url: process.env.NEON_REALTIME_URL,
    branch: process.env.NEON_BRANCH || "production",
    branchId: process.env.NEON_BRANCH_ID || "br-patient-union-bdtf9eqy",
  };

  return NextResponse.json(results);
}

