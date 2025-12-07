/**
 * API Proxy Route Handler
 *
 * Forwards all /api/v1/* requests to the backend API server
 * localhost:3000/api/v1/projects -> localhost:8000/api/v1/projects
 *
 * Supports streaming responses (SSE) for endpoints like /stream
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

async function proxyRequest(request: NextRequest, method: string) {
  try {
    const { pathname, search } = request.nextUrl;
    const backendUrl = `${API_BASE_URL}${pathname}${search}`;

    console.log(`[Proxy] ${method} ${pathname}${search} -> ${backendUrl}`);

    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    // Add body for POST/PUT/PATCH
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
      const body = await request.text();
      if (body) options.body = body;
    }

    const response = await fetch(backendUrl, options);
    const contentType = response.headers.get('content-type') || '';

    // Check if this is a streaming response (SSE)
    if (contentType.includes('text/event-stream')) {
      console.log(`[Proxy] Streaming response detected for ${pathname}`);

      // For streaming responses, pass through the body directly
      if (!response.body) {
        return new NextResponse('No response body', { status: 502 });
      }

      // Create a TransformStream to pass through the data
      const { readable, writable } = new TransformStream();

      // Pipe the response body to our transform stream
      response.body.pipeTo(writable).catch((err) => {
        console.error('[Proxy] Stream pipe error:', err);
      });

      return new NextResponse(readable, {
        status: response.status,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no',
        },
      });
    }

    // For non-streaming responses, read the full body
    const data = await response.text();

    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': contentType || 'application/json',
      },
    });
  } catch (error) {
    console.error('[Proxy] Error:', error);
    return NextResponse.json(
      { success: false, error: 'Proxy failed' },
      { status: 502 }
    );
  }
}

export async function GET(request: NextRequest) {
  return proxyRequest(request, 'GET');
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, 'POST');
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request, 'PUT');
}

export async function PATCH(request: NextRequest) {
  return proxyRequest(request, 'PATCH');
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request, 'DELETE');
}
