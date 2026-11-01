import { NextResponse } from 'next/server';
import { extractNameFromFilename } from '@/lib/parseFile';

export const dynamic = 'force-dynamic';
export const maxDuration = 120; // 2 minutes max processing

export async function POST(req) {
  const authHeader = req.headers.get('authorization');
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      return NextResponse.json({ error: 'NEXT_PUBLIC_BACKEND_URL is not configured' }, { status: 500 });
    }

    const formData = await req.formData();
    const file = formData.get('file'); // 'file' matches the FormData key in ResumeUpload.jsx
    const jdText = formData.get('jdText') || "General Software Engineering Role"; // Optional role hint
    const targetSkillsRaw = formData.get('targetSkills') || '';

    const user_id = formData.get('user_id') || 'demo';

    if (!file) {
      return NextResponse.json(
        { error: 'At least one resume file is required' },
        { status: 400 }
      );
    }

    const name = extractNameFromFilename(file.name);
    const uploadForm = new FormData();
    uploadForm.append('file', file);
    const uploadRes = await fetch(`${backendUrl}/api/resume/upload`, {
      method: 'POST',
      headers: { ...(authHeader ? { Authorization: authHeader } : {}) },
      body: uploadForm,
    });
    
    let uploadData;
    const uploadContentType = uploadRes.headers.get("content-type");
    if (uploadContentType && uploadContentType.includes("application/json")) {
      uploadData = await uploadRes.json();
    } else {
      uploadData = { detail: await uploadRes.text() };
    }

    if (!uploadRes.ok) {
      return NextResponse.json({ error: uploadData?.detail || 'Resume upload failed' }, { status: uploadRes.status });
    }

    const analyzeRes = await fetch(`${backendUrl}/api/resume/analyze`, {
      method: 'POST',
      headers: {
        ...(authHeader ? { Authorization: authHeader } : {}), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id,
        file_id: uploadData.file_id,
        role_target: jdText,
        target_skills: String(targetSkillsRaw)
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        use_llm: true,
      }),
    });
    
    let analyzeData;
    const analyzeContentType = analyzeRes.headers.get("content-type");
    if (analyzeContentType && analyzeContentType.includes("application/json")) {
      analyzeData = await analyzeRes.json();
    } else {
      analyzeData = { detail: await analyzeRes.text() };
    }

    if (!analyzeRes.ok) {
      return NextResponse.json({ error: analyzeData?.detail || 'Resume analysis failed' }, { status: analyzeRes.status });
    }
    const analysis = analyzeData.analysis || {};

    // Return shape expected by existing UI components
    return NextResponse.json({
      name,
      fileId: uploadData.file_id,
      resultId: analyzeData.result_id,
      fileUrl: null,
      resumeText: uploadData.text_preview || '',
      score: analysis.score || 0,
      skills: analysis.skills || [],
      weaknesses: analysis.weaknesses || [],
      recommendations: analysis.recommended_roles || [],
      domain: analysis.experience_level || 'unknown',
      sectionReviews: analysis.section_reviews || [],
      detailedReview: analysis.detailed_review || {},
      aiAnalyzed: true,
      analysisVersion: 'v2',
    }, { status: 200 });

  } catch (error) {
    console.error('Screening error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
