from django import forms
from .models import Lessor


class LessorForm(forms.ModelForm):
    class Meta:
        model = Lessor
        fields = '__all__'  # Включаем все поля модели Lessor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            user = self.instance.user
            # Добавляем поля из связанной модели User в форму
            for field in ['email', 'first_name', 'last_name', 'date_of_birth', 'telephone', 'currency', 'avatar', 'about', 'email_notification', 'push_notification']:
                if field not in self.fields:
                    self.fields[field] = forms.CharField(
                        label=user._meta.get_field(field).verbose_name,
                        initial=getattr(user, field),
                        required=False,
                    )
