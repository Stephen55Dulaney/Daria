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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchResult {
  id: string;
  title: string;
  participant_name: string;
  created_at: string;
  preview: string;
  tags: string[];
  match_context?: string;
  confidence?: number;
}

interface AdvancedSearchProps {
  onSearch: (params: SearchParams) => void;
  results: SearchResult[];
  loading?: boolean;
}

interface SearchParams {
  query: string;
  searchType: 'semantic' | 'exact' | 'fuzzy';
  dateRange: 'all' | 'week' | 'month' | 'year';
  tags: string[];
}

const SearchResultCard = ({ result }: { result: SearchResult }) => {
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
      >
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="h6">{result.title}</Typography>
            {result.confidence && (
              <Chip 
                label={`${(result.confidence * 100).toFixed(0)}% Match`}
                color={result.confidence > 0.7 ? "success" : "warning"}
                size="small"
              />
            )}
          </Box>
          
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            {result.participant_name} • {new Date(result.created_at).toLocaleDateString()}
          </Typography>

          <Typography variant="body2" color="text.secondary" paragraph>
            {result.match_context || result.preview}
          </Typography>

          <Box display="flex" gap={1} flexWrap="wrap">
            {result.tags.map((tag, idx) => (
              <Chip key={idx} label={tag} size="small" />
            ))}
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export const AdvancedSearch: React.FC<AdvancedSearchProps> = ({
  onSearch,
  results,
  loading = false,
}) => {
  const [searchParams, setSearchParams] = useState<SearchParams>({
    query: '',
    searchType: 'semantic',
    dateRange: 'all',
    tags: [],
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchParams);
  };

  const handleClear = () => {
    setSearchParams({
      query: '',
      searchType: 'semantic',
      dateRange: 'all',
      tags: [],
    });
  };

  return (
    <Container maxWidth="lg">
      <Box component="form" onSubmit={handleSearch} mb={4}>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Search interviews..."
              value={searchParams.query}
              onChange={(e) => setSearchParams({ ...searchParams, query: e.target.value })}
              InputProps={{
                endAdornment: (
                  <IconButton type="submit" disabled={loading}>
                    {loading ? <CircularProgress size={24} /> : <SearchIcon />}
                  </IconButton>
                ),
              }}
            />
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth variant="outlined">
              <InputLabel>Search Type</InputLabel>
              <Select
                value={searchParams.searchType}
                onChange={(e) => setSearchParams({ ...searchParams, searchType: e.target.value as 'semantic' | 'exact' | 'fuzzy' })}
                label="Search Type"
              >
                <MenuItem value="semantic">Semantic Search</MenuItem>
                <MenuItem value="exact">Exact Match</MenuItem>
                <MenuItem value="fuzzy">Fuzzy Match</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={4}>
            <FormControl fullWidth variant="outlined">
              <InputLabel>Date Range</InputLabel>
              <Select
                value={searchParams.dateRange}
                onChange={(e) => setSearchParams({ ...searchParams, dateRange: e.target.value as 'all' | 'week' | 'month' | 'year' })}
                label="Date Range"
              >
                <MenuItem value="all">All Time</MenuItem>
                <MenuItem value="week">Past Week</MenuItem>
                <MenuItem value="month">Past Month</MenuItem>
                <MenuItem value="year">Past Year</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={4}>
            <Box display="flex" gap={1}>
              <Button
                variant="contained"
                startIcon={<FilterIcon />}
                onClick={handleSearch}
                disabled={loading}
                fullWidth
              >
                Apply Filters
              </Button>
              <Button
                variant="outlined"
                startIcon={<ClearIcon />}
                onClick={handleClear}
                disabled={loading}
              >
                Clear
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Box>

      <AnimatePresence>
        <Grid container spacing={3}>
          {results.map((result, idx) => (
            <Grid item xs={12} md={6} key={idx}>
              <SearchResultCard result={result} />
            </Grid>
          ))}
        </Grid>
      </AnimatePresence>
    </Container>
  );
}; 