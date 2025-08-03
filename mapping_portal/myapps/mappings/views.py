from django.shortcuts import render, redirect
from myapps.accounts.models import UserData
from myapps.mappings.forms import CustomLoginForm
from myapps.mappingmaintain.models import JoinConditions, ApplicationCode, Mappings, MappingAudit
from django.utils import timezone
from django.contrib import messages



def login(request):
    print("✅ login view called")
    return render(request,'myapps/mappings/templates/mappings/login.html')

def news(request):
    return render(request,'myapps/mappings/templates/mappings/news.html')
def contact(request):
    return render(request,'myapps/mappings/templates/mappings/contact.html')
def about(request):
    return render(request,'myapps/mappings/templates/mappings/about.html')

##Login user validation

def custom_login(request):
    print("✅ custom_login view called")
    error = None

    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            lan_id = form.cleaned_data['lan_id']
            password = form.cleaned_data['password']

            try:
                user = UserData.objects.get(user_id=lan_id, password=password)
                request.session['user_id'] = user.user_id
                print("✅ LOGIN OK:", lan_id)
                return redirect('mappings:home')
            except UserData.DoesNotExist:
                print("❌ User not found")
                error = "Invalid LAN ID or password."
        else:
            print("Form is invalid:", form.errors)
    else:
        form = CustomLoginForm()

    return render(request, 'mappings/login.html', {'form': form, 'error': error})

def home(request):
    if 'user_id' not in request.session:
        return redirect('custom_login')

    print("✅ Entered home view")

    # Build a dictionary {app_code: [file1, file2]} using target_app_code
    appcode_files = {}
    files = Mappings.objects.values_list('uploaded_file', 'target_app_code').distinct()
    print(f"🔍 Found mapping files: {files}")
    for file_name, app_code in files:
        if app_code not in appcode_files:
            appcode_files[app_code] = []
        appcode_files[app_code].append(file_name)

    selected_file = request.GET.get('file')
    print(f"📂 Selected file from request: {selected_file}")

    mappings = Mappings.objects.filter(uploaded_file=selected_file) if selected_file else None
    joins = JoinConditions.objects.filter(uploaded_file=selected_file) if selected_file else None

    print(f"📊 Fetched {mappings.count() if mappings else 0} mappings")
    print(f"🔗 Fetched {joins.count() if joins else 0} join conditions")

    if request.method == 'POST':
        user_id = request.session.get('user_id', 'unknown')

        # --- Update JoinConditions ---
        if joins:
            for join in joins:
                prefix = f"join_{join.pk}"
                new_mapping_ref_name = request.POST.get(f"{prefix}_mapping_ref_name", "").strip()
                new_table_1 = request.POST.get(f"{prefix}_table_1", "").strip()
                new_table_2 = request.POST.get(f"{prefix}_table_2", "").strip()
                new_join = request.POST.get(f"{prefix}_join", "").strip()

                if (
                    join.mapping_ref_name != new_mapping_ref_name or
                    join.table_1 != new_table_1 or
                    join.table_2 != new_table_2 or
                    join.join != new_join
                ):
                    join.mapping_ref_name = new_mapping_ref_name
                    join.table_1 = new_table_1
                    join.table_2 = new_table_2
                    join.join = new_join
                    join.save()

                    # Create audit entry for JoinConditions update
                    MappingAudit.objects.create(
                        app_code=request.POST.get('app_code', ''),
                        uploaded_file=selected_file,
                        action='update',
                        performed_by=user_id,
                        remarks=f'JoinConditions updated for file {selected_file}'
                    )

        # --- Update Mappings ---
        if mappings:
            for mapping in mappings:
                prefix = f"mapping_{mapping.s_no}"
                updated = False

                new_values = {
                    "target_app_code": request.POST.get(f"{prefix}_target_app_code", "").strip(),
                    "target_table_name": request.POST.get(f"{prefix}_target_table_name", "").strip(),
                    "target_column_name_physical": request.POST.get(f"{prefix}_target_column_name_physical", "").strip(),
                    "source_app_code": request.POST.get(f"{prefix}_source_app_code", "").strip(),
                    "source_table_name": request.POST.get(f"{prefix}_source_table_name", "").strip(),
                    "country_applicability": request.POST.get(f"{prefix}_country_applicability", "").strip(),
                    "source_column_name_physical": request.POST.get(f"{prefix}_source_column_name_physical", "").strip(),
                }

                for field, new_value in new_values.items():
                    if getattr(mapping, field) != new_value:
                        setattr(mapping, field, new_value)
                        updated = True

                if updated:
                    mapping.save()
                    # Create audit entry for Mappings update
                    MappingAudit.objects.create(
                        app_code=request.POST.get('app_code', ''),
                        uploaded_file=selected_file,
                        action='update',
                        performed_by=user_id,
                        remarks=f'Mapping fields updated for file {selected_file}'
                    )

        messages.success(request, "✅ Changes saved successfully.")
        return redirect(f"{request.path}?file={selected_file}")

    return render(request, 'mappings/home.html', {
        'appcode_files': appcode_files,
        'mappings': mappings,
        'joins': joins,
        'selected_file': selected_file
    })


def edit_mapping_file(request, file_name):
    if 'user_id' not in request.session:
        return redirect('custom_login')

    mappings = Mappings.objects.filter(uploaded_file=file_name)

    if request.method == 'POST':
        for mapping in mappings:
            prefix = f"mapping_{mapping.id}"
            mapping.source_field = request.POST.get(f"{prefix}_source_field", "")
            mapping.target_field = request.POST.get(f"{prefix}_target_field", "")
            mapping.transformation_logic = request.POST.get(f"{prefix}_transformation_logic", "")
            mapping.save()
        return redirect('home')

    return render(request, 'mappings/edit_mapping.html', {
        'file_name': file_name,
        'mappings': mappings
    })
