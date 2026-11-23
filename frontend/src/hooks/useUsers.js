import { useQuery } from '@tanstack/react-query'
import userService from '../services/userService'

export function useUsers(params = {}) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => userService.list(params),
  })
}
