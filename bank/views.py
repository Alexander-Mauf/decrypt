import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from core import models
from . import serializers
from .forms import CreateTransferForm
from .models import BankUserAdministration

def test(request):
    try:
        bankaccounts = request.user.bank_customer.account_owned_by.all()
        # transfers muss erweitert werden um die transfers, wo man empfänger oder ersteller ist
        transfers = request.user.bank_customer.created_by.all()

    except Exception as e:
        return redirect(reverse('bank_index'))
    if request.user.is_authenticated:
        return render(request, 'transfer.html', {
            "user": request.user,
            "accounts": bankaccounts,
            "transfers": transfers
        })
    else:
        return redirect(reverse('bank_index'))


def login_view(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            return redirect(reverse('loadhome'))
        return render(request, "login.html")
    if request.method == "POST":
        # getting usernames as post from login
        usname = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=usname, password=password)
        if user is not None:
            login(request, user)
        if request.user.is_authenticated:
            return redirect(reverse('loadhome'))
        else:
            return redirect(reverse('login_failed'))



def logout_view(request):
    logout(request)
    return redirect(reverse('bank_index'))


def loadhome(request):
    if request.user.is_authenticated:
        bankaccounts = request.user.bank_customer.account_owned_by.all()
        transfers = request.user.bank_customer.created_by.all()
        print(bankaccounts)
        return render(request, 'transfer.html', {
            "user": request.user,
            "accounts": bankaccounts,
            "transfers": transfers
        })
    else:
        return redirect(reverse('bank_login_failed'))

def login_failed(request):
    return render(request, "login.html", {
        "statusmsg": "Username or Password unknown"
    })

def index(request):
    if request.user.is_authenticated:
        return redirect(reverse('loadhome'))
    return redirect(reverse('login_view'))


def signup(request):
    if request.method == "GET":
        # prüfen ob schon eingeloggt
        if request.user.is_authenticated:
            return redirect(reverse('loadhome'))
        return render(request, "signup.html")

    if request.method == "POST":
        # POST
        # get data from a form
        vorname = request.POST.get("vorname")
        nachname = request.POST.get("name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        passwordcheck = request.POST.get("passwordcheck")
        if password != passwordcheck:
            return render(request, "signup.html", {
                "statusmsg": "Passwörter stimmen nicht überein.",
            })
        else:
            # user wird erstellt

            user = User.objects.create_user(username, email, password, first_name=vorname, last_name=nachname)
            user.save()
            user = User.objects.get(username=username)

            # user wird der folgenden rechtegruppe zugewiesen

            group = Group.objects.get(name='Bankkunden')
            group.user_set.add(user)
            group.save()

            customer = models.BankCustomer.objects.create(
                user=user,
                adress="",
            )
            customer.save()

            account = models.BankAccount.objects.create(
                name="geld",
                account_owned_by=customer
            )
            account.save()

            # die Rechtezuweisung ist dopelt gemoppelt jedoch ist keine Bankkunden Group
            # programmatisch festgehalten diese wurde via Django-Admin interface erstellt
            # vermutlich kann ich den folgenden code in der admin.py datein an der richtigen
            # Stelle anbringen um die Gruppe auch bei Datenbankverlust erhalten zu lassen.
            codenames = [
                'view_banktransfer',
                'add_banktransfer',
                'view_bankaccount',
                'view_bankcustomer',
                'change_bankcustomer',
            ]
            permissions = Permission.objects.filter(codename__in=codenames).all()

            user.user_permissions.set(permissions)
            user.save()

            return render(request, "login.html")


def update_adress(request, user_id):
    user = User.objects.get(pk=user_id)
    newadress = request.POST.get("adress")
    user.BankCustomer.adress = newadress
    user.save()

class CreateTransferView(FormView):
    form_class = CreateTransferForm
    lang = 'de'

    def get(self, request, *args, **kwargs):
        errors = request.session.get("core.login.errors")
        errors = json.loads(errors) if errors is not None else {}
        request.session["core.login.errors"] = None
        form = self.get_form()
        if request.user.is_authenticated:
            return redirect(reverse('home'))
        if errors is not None:
            errors = [",".join(v) for k, v in errors.items()]
            errors = "<br>".join(errors) if len(errors) > 0 else None
        return render(request, 'login.html', {'form': form, 'errors': errors})

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            cd = form.cleaned_data
            cd.get("")

            # logik erstellen des ransfers

            #user = authenticate(request, username=cd.get("username"), password=cd.get("password"))
            #if user is not None:
            #    login(request, user)
            #if request.user.is_authenticated:
            #    return redirect(reverse('home'))
            #else:
            #    request.session['core.login.errors'] = json.dumps({"password": [_(
            #        "<strong>Der Benutzername oder das Passwort ist ungültig.</strong><br>Beide Felder berücksichtigen die Groß-/Kleinschreibung.")]})
            #    return redirect(reverse('user_login'))
        request.session['core.login.errors'] = json.dumps(form.errors)
        return redirect(reverse('user_login'))


def create_transfer(request):
    bankaccounts = request.user.bank_customer.account_owned_by.all()

    if request.method == "GET":
        return render(request, 'home2.html', {
            "user": request.user,
            "accounts": bankaccounts,
            "statusmsg": None,
        })

    if request.method == "POST":
        iban_to = request.POST.get("iban_to")
        iban_from = request.POST.get("iban_from")
        amount = request.POST.get("amount")
        use_case = request.POST.get("verwendungszweck")
        instant_transfer = request.POST.get("Sofortüberweisung", False)

        amount = amount.replace(",", ".")
        amount = Decimal(amount)
        print(
            iban_from,
            iban_to,
            amount,
            use_case,
            instant_transfer,
        )
        created_by = request.user.bank_customer
        try:
            iban_to = models.BankAccount.objects.get(iban=iban_to)
        except Exception as e:
            return render(request, 'home2.html', {
                "user": request.user,
                "accounts": bankaccounts,
                "statusmsg": "Zieladresse Existiert nicht",
            })


        iban_from = models.BankAccount.objects.get(iban=iban_from)

        # if BankAccount.objects.get(iban=request.POST.get("iban_to")):
        #if
        try:
            with transaction.atomic():
                # warum erstelle ich hier eine instanz wenn ich die information auch an die API
                # senden könnte
                # POST /bank/api/bank-transfers
                transfer = models.BankTransfer.objects.create(
                    iban_to=iban_to,
                    iban_from=iban_from,
                    amount=amount,
                    use_case=use_case,
                    created_by=created_by
                )
                transfer.save()
        except Exception as e:
            print(e)
            return render(request, 'transfer.html', {
                "user": request.user,
                "accounts": bankaccounts,
                "statusmsg": "ERSTELLEN Fehlgeschlagen",
            })

        # muss das hier nochmal seperat in eine transaction.atomic() gepackt werden?
        # nein  dies wird innerhalb der run_transfer() funktion gehandelt
        if instant_transfer == "on":
            transfer.execute_datetime = timezone.now
            transfer.run_transfer()

        return render(request, 'transfer.html', {
            "user": request.user,
            "accounts": bankaccounts,
            "statusmsg": transfer.executionlog,
        })

        # Unterscheidung success nicht success

    # else:

    #   return render(request, 'home2.html', {
    #       "user": request.user,
    #       "accounts": bankaccounts,
    #       "statusmsg": "Es ist ein Fehler aufgetreten.",
    #   })
    #

    # man könnte hier auch den transfer direkt ausführen
    #
    # User.bank_customer.account_owned_by.balance = User.bank_customer.account_owned_by.balance - amount
    # User.bank_customer.account_owned_by.balance = User.bank_customer.account_owned_by.balance + amount
    # both.save()

    bankaccounts = BankUserAdministration(request.user).adminstrating_accounts
    return render(request, 'home2.html', {
        "user": request.user,
        "accounts": bankaccounts,
        "statusmsg": "Überweisung erfolgreich erstellt",
    })


class BankCustomerViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.BankCustomersSerializer
    queryset = models.BankCustomer.objects.order_by('id').all()
    permission_classes = [IsAuthenticated]  # (IsAuthenticated, DjangoModelPermission)
    authentication_classes = (SessionAuthentication,
                              BasicAuthentication)  # zur authorisierung und errfüllung des tests(SessionAuthentication, BasicAuthentication)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_fields = {
        # 'name':['exact'],
        'adress': ['exact'],
        'created_at': ['gte', 'lte'],
        'updated_at': ['gte', 'lte'],
    }

    def create(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super(BankCustomerViewSet, self).get_queryset()
        else:
            return super(BankCustomerViewSet, self).get_queryset().filter(user=user)


class BankTransferViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.BankTransferSerializer
    queryset = models.BankTransfer.objects.all()
    permission_classes = [IsAuthenticated]  # (IsAuthenticated, DjangoModelPermission)
    authentication_classes = (SessionAuthentication,
                              BasicAuthentication)  # zur authorisierung und errfüllung des tests(SessionAuthentication, BasicAuthentication)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super(BankTransferViewSet, self).get_queryset()
        else:
            return super(BankTransferViewSet, self).get_queryset().filter(
                Q(iban_from=user.bank_customer.account_owned_by) |
                Q(iban_to=user.bank_customer.account_owned_by) |
                Q(created_by=user.bank_customer)
            )

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    #def create(self, request):
    #    user = self.request.user
    #    if (Q())
    #    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class BankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.BankAccountSerializer
    queryset = models.BankAccount.objects.all()
    permission_classes = [IsAuthenticated]  # (IsAuthenticated, DjangoModelPermission)
    authentication_classes = (SessionAuthentication,
                              BasicAuthentication)  # zur authorisierung und errfüllung des tests(SessionAuthentication, BasicAuthentication)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super(BankAccountViewSet, self).get_queryset()
        else:
            return super(BankAccountViewSet, self).get_queryset().filter(
                account_owned_by=user.bank_customer)  # hier muss ein "or" hin

    def create(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
