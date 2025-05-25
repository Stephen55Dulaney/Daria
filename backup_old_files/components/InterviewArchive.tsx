import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Container,
  Grid,
  Typography,
  TextField,
  IconButton,
  Button,
  Chip,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  CalendarToday as CalendarIcon,
  Person as PersonIcon,
  Label as LabelIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

interface Interview {
  id: string;
  title: string;
  participant_name: string;
  created_at: string;
  preview: string;
  tags: string[];
  status: 'draft' | 'in_progress' | 'completed';
}

interface InterviewArchiveProps {
  interviews: Interview[];
  onSearch: (query: string) => void;
  onInterviewClick: (id: string) => void;
  loading?: boolean;
}

const InterviewCard = ({ interview, onClick }: { interview: Interview; onClick: () => void }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return { bg: '#e6f4ea', text: '#1e7e34' };
      case 'in_progress':
        return { bg: '#fff3e0', text: '#e65100' };
      default:
        return { bg: '#f5f5f5', text: '#666666' };
    }
  };

  const statusColors = getStatusColor(interview.status);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <Card 
        sx={{ 
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: 4,
          }
        }}
        onClick={onClick}
      >
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">{interview.title}</Typography>
            <Chip 
              label={interview.status.replace('_', ' ')}
              size="small"
              sx={{
                backgroundColor: statusColors.bg,
                color: statusColors.text,
                textTransform: 'capitalize',
              }}
            />
          </Box>

          <Box display="flex" alignItems="center" gap={1} mb={1}>
            <PersonIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {interview.participant_name}
            </Typography>
          </Box>

          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <CalendarIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {new Date(interview.created_at).toLocaleDateString()}
            </Typography>
          </Box>

          <Typography variant="body2" color="text.secondary" paragraph>
            {interview.preview}
          </Typography>

          <Divider sx={{ my: 2 }} />

          <Box display="flex" gap={1} flexWrap="wrap">
            {interview.tags.map((tag, idx) => (
              <Chip
                key={idx}
                label={tag}
                size="small"
                icon={<LabelIcon />}
                variant="outlined"
              />
            ))}
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export const InterviewArchive: React.FC<InterviewArchiveProps> = ({
  interviews,
  onSearch,
  onInterviewClick,
  loading = false,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  return (
    <Container maxWidth="lg">
      <Box mb={4}>
        <Typography variant="h4" gutterBottom>
          Interview Archive
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Browse and search through your interview sessions
        </Typography>

        <Box component="form" onSubmit={handleSearch}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search interviews by title, participant, or content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              endAdornment: (
                <IconButton type="submit" disabled={loading}>
                  {loading ? <CircularProgress size={24} /> : <SearchIcon />}
                </IconButton>
              ),
            }}
          />
        </Box>
      </Box>

      <AnimatePresence>
        <Grid container spacing={3}>
          {interviews.map((interview, idx) => (
            <Grid item xs={12} md={6} key={idx}>
              <InterviewCard
                interview={interview}
                onClick={() => onInterviewClick(interview.id)}
              />
            </Grid>
          ))}
        </Grid>
      </AnimatePresence>

      {interviews.length === 0 && !loading && (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No interviews found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try adjusting your search or start a new interview
          </Typography>
          <Button
            variant="contained"
            color="primary"
            href="/interview_setup"
            sx={{ mt: 2 }}
          >
            Start New Interview
          </Button>
        </Box>
      )}
    </Container>
  );
}; 