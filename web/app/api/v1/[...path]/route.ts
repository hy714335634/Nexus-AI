/**
 * API Proxy Route Handler
 *
 * Forwards all /api/v1/* requests to the backend API server
 * localhost:3000/api/v1/projects -> localhost:8000/api/v1/projects
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
    const data = await response.text();

    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'application/json',
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