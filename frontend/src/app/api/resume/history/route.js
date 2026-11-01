import { NextResponse } from 'next/server';

export async function GET(req) {
  const authHeader = req.headers.get('authorization');
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      return NextResponse.json({ error: 'NEXT_PUBLIC_BACKEND_URL is not configured' }, { status: 500 });
    }

    const { searchParams } = new URL(req.url);
    const limit = searchParams.get('limit') || '10';
    const userId = searchParams.get('user_id');

    let fetchUrl = `${backendUrl}/api/resume/history?limit=${encodeURIComponent(limit)}`;
    if (userId) {
        fetchUrl += `&user_id=${encodeURIComponent(userId)}`;
    }

    const response = await fetch(fetchUrl, {
      method: 'GET',
      headers: { ...(authHeader ? { Authorization: authHeader } : {}) },
      cache: 'no-store',
    });
    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json({ error: data?.detail || 'Failed to load resume history' }, { status: response.status });
    }

    return NextResponse.json({ history: data.history || [] }, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
