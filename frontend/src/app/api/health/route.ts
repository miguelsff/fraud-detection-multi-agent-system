import { NextResponse } from "next/server";

/**
 * Health check endpoint for Docker healthcheck and monitoring.
 * GET /api/health
 */
export async function GET() {
  return NextResponse.json(
    {
      status: "healthy",
      timestamp: new Date().toISOString(),
      service: "fraud-detection-frontend",
    },
    { status: 200 }
  );
}
