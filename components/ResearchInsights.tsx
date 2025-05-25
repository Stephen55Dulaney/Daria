import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Container,
  Grid,
  Typography,
  TextField,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  Lightbulb as LightbulbIcon,
  Category as CategoryIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { InsightType, UXInsight } from '../core/llm_analyzer';

interface Quote {
  text: string;
  speaker: string;
  timestamp: string;
}

interface ResearchInsightsProps {
  insights: UXInsight[];
  onSearch: (query: string) => void;
  loading?: boolean;
}

const InsightTypeIcon = ({ type }: { type: InsightType }) => {
  switch (type) {
    case InsightType.BEHAVIORAL:
      return <TrendingUpIcon />;
    case InsightType.PAIN_POINT:
      return <WarningIcon />;
    case InsightType.OPPORTUNITY:
      return <LightbulbIcon />;
    case InsightType.THEME:
      return <CategoryIcon />;
    default:
      return null;
  }
};

const InsightCard = ({ insight }: { insight: UXInsight }) => {
  const [expanded, setExpanded] = useState(false);

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
        onClick={() => setExpanded(!expanded)}
      >
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <InsightTypeIcon type={insight.type} />
            <Typography variant="subtitle1" color="text.secondary">
              {insight.type}
            </Typography>
            <Box flexGrow={1} />
            <Tooltip title={`Confidence: ${(insight.confidence * 100).toFixed(0)}%`}>
              <CircularProgress
                variant="determinate"
                value={insight.confidence * 100}
                size={24}
                sx={{ color: insight.confidence > 0.7 ? 'success.main' : 'warning.main' }}
              />
            </Tooltip>
          </Box>

          <Typography variant="h6" gutterBottom>
            {insight.content}
          </Typography>

          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                {insight.context.sub_themes && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>
                      Sub-themes
                    </Typography>
                    <Box display="flex" gap={1} flexWrap="wrap">
                      {insight.context.sub_themes.map((theme: string, idx: number) => (
                        <Chip key={idx} label={theme} size="small" />
                      ))}
                    </Box>
                  </Box>
                )}

                {insight.supporting_quotes.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>
                      Supporting Quotes
                    </Typography>
                    {insight.supporting_quotes.map((quote: string, idx: number) => (
                      <Card key={idx} variant="outlined" sx={{ mt: 1, bgcolor: 'grey.50' }}>
                        <CardContent>
                          <Typography variant="body1">
                            "{quote}"
                          </Typography>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                )}

                {insight.context.potential_solution && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>
                      Potential Solution
                    </Typography>
                    <Typography variant="body1">
                      {insight.context.potential_solution}
                    </Typography>
                  </Box>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export const ResearchInsights: React.FC<ResearchInsightsProps> = ({
  insights,
  onSearch,
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
        <form onSubmit={handleSearch}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search insights..."
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
        </form>
      </Box>

      <Grid container spacing={3}>
        {insights.map((insight, idx) => (
          <Grid item xs={12} md={6} key={idx}>
            <InsightCard insight={insight} />
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}; 