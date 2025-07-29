from django.http import JsonResponse
from django.views import View
import json
import logging

from .models import Skill, Expertise

logger = logging.getLogger(__name__)


class SkillsAPIView(View):
    def get(self, request):
        """List all skills with optional search filtering"""
        search_term = request.GET.get('search', '').strip()
        
        if search_term:
            skills = list(Skill.objects.filter(name__icontains=search_term).values('id', 'name'))
        else:
            skills = list(Skill.objects.values('id', 'name'))
            
        return JsonResponse(skills, safe=False)
    
    def post(self, request):
        """Create a new skill"""
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            
            if not name:
                return JsonResponse({'error': 'Name is required'}, status=400)
            
            skill, created = Skill.objects.get_or_create(name=name)
            
            if created:
                return JsonResponse({
                    'skill': {'id': skill.id, 'name': skill.name},
                    'created': True
                }, status=201)
            else:
                return JsonResponse({
                    'skill': {'id': skill.id, 'name': skill.name},
                    'created': False
                }, status=200)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({'error': 'An internal error has occurred.'}, status=500)


class SkillDetailAPIView(View):
    def delete(self, request, skill_id):
        """Hard delete a skill"""
        try:
            skill = Skill.objects.get(id=skill_id)
            skill.delete()
            return JsonResponse({'success': True}, status=200)
        except Skill.DoesNotExist:
            return JsonResponse({'error': 'Skill not found'}, status=404)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({'error': 'An internal error has occurred.'}, status=500)


class ExpertisesAPIView(View):
    def get(self, request):
        """List all expertises with optional search filtering"""
        search_term = request.GET.get('search', '').strip()
        
        if search_term:
            expertises = list(Expertise.objects.filter(name__icontains=search_term).values('id', 'name'))
        else:
            expertises = list(Expertise.objects.values('id', 'name'))
            
        return JsonResponse(expertises, safe=False)
    
    def post(self, request):
        """Create a new expertise"""
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            
            if not name:
                return JsonResponse({'error': 'Name is required'}, status=400)
            
            expertise, created = Expertise.objects.get_or_create(name=name)
            
            if created:
                return JsonResponse({
                    'expertise': {'id': expertise.id, 'name': expertise.name},
                    'created': True
                }, status=201)
            else:
                return JsonResponse({
                    'expertise': {'id': expertise.id, 'name': expertise.name},
                    'created': False
                }, status=200)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({'error': 'An internal error has occurred.'}, status=500)


class ExpertiseDetailAPIView(View):
    def delete(self, request, expertise_id):
        """Hard delete an expertise"""
        try:
            expertise = Expertise.objects.get(id=expertise_id)
            expertise.delete()
            return JsonResponse({'success': True}, status=200)
        except Expertise.DoesNotExist:
            return JsonResponse({'error': 'Expertise not found'}, status=404)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({'error': 'An internal error has occurred.'}, status=500)