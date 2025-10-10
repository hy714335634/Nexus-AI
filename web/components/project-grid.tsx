import type { ProjectSummary } from '@/types/projects';
import { ProjectCard } from '@components/project-card';

interface ProjectGridProps {
  readonly projects: ProjectSummary[];
}

export function ProjectGrid({ projects }: ProjectGridProps) {
  if (!projects.length) {
    return <div style={{ color: 'var(--muted)' }}>目前没有构建项目。</div>;
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: '24px',
      }}
    >
      {projects.map((project) => (
        <ProjectCard key={project.projectId} project={project} />
      ))}
    </div>
  );
}
