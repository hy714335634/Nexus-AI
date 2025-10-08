import { ProjectDetailView } from './project-detail-view';

interface ProjectDetailPageProps {
  params: { id: string };
}

export default function ProjectDetailPage({ params }: ProjectDetailPageProps) {
  const projectId = decodeURIComponent(params.id);
  return <ProjectDetailView projectId={projectId} />;
}
